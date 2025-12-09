# services/playwright_scraper_service.py

import asyncio
from datetime import datetime
from typing import Optional, Tuple
from config.settings import settings
from services.repositories.price_repo import PriceRepository
from services.websocket_manager import manager as ws_manager
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError


class PlaywrightGoldScrapingService:
    def __init__(self, repo: PriceRepository):
        self.repo = repo
        self.browser: Optional[Browser] = None

    # --- Setup Browser ---
    async def _setup_browser(self) -> Tuple[Browser, Page]:
        if not self.browser:
            p = await async_playwright().start()
            self.browser = await p.chromium.launch(headless=True)
        page = await self.browser.new_page()
        await page.set_viewport_size({"width": 1400, "height": 900})
        return self.browser, page

    # --- Close Browser ---
    async def _close_browser(self):
        if self.browser:
            await self.browser.close()
            print("Playwright Browser closed.")
            self.browser = None

    # --- Scrape price from website ---
    async def _fetch_scraping_price_async(self) -> Optional[Tuple[str, str]]:
        page: Optional[Page] = None
        try:
            _, page = await self._setup_browser()
            await page.goto(settings.FAILOVER_URL, wait_until="domcontentloaded", timeout=60000)

            # Handle cookie/consent popup
            try:
                consent_locator = page.locator(
                    "button:has-text('Accept'):visible, button:has-text('OK'):visible"
                )
                await consent_locator.click(timeout=5000)
            except PlaywrightTimeoutError:
                pass

            price_selector = settings.FAILOVER_CSS_SELECTOR
            price_locator = page.locator(price_selector)
            await price_locator.wait_for(state="visible", timeout=30000)

            current_price = await price_locator.inner_text()
            return current_price.strip(), "IG.com (Playwright)"

        except PlaywrightTimeoutError as e:
            print(f"Scraping Timeout: {e}")
            return None, None
        except Exception as e:
            print(f"Scraping Error: {e}")
            return None, None
        finally:
            if page:
                await page.close()

    # --- Main async scraping loop ---
    async def run_scraper_loop_async(self, mongo_client: MongoClient):
        print("Dual-Source Async Scraper started.")
        try:
            while True:
                current_price, current_source = await self._fetch_scraping_price_async()

                if not current_price:
                    print("Warning: Failed to fetch price. Retrying...")
                    await asyncio.sleep(settings.SCRAPE_INTERVAL_SECONDS)
                    continue

                print(f"DEBUG: Price Check: '{current_price}' | Source: '{current_source}'")

                # --- Save to MongoDB ---
                try:
                    await self.repo.save_price(mongo_client, current_price, current_source)
                    print(f"Saved price to MongoDB: {current_price}")
                except Exception as e:
                    print(f"Error saving to MongoDB: {e}")

                # --- Broadcast to WebSocket clients ---
                try:
                    data_to_push = {
                        "price": current_price,
                        "source": current_source,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    await ws_manager.broadcast(data_to_push)
                except Exception as e:
                    print(f"Error broadcasting WebSocket data: {e}")

                await asyncio.sleep(settings.SCRAPE_INTERVAL_SECONDS)

        finally:
            # Cleanup browser on exit
            if self.browser:
                await self._close_browser()

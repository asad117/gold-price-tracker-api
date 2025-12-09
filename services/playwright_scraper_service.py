# playwright_scraper_service.py
import asyncio
from datetime import datetime
from typing import Optional, Awaitable, Any, Tuple
from pymongo import MongoClient
from config.settings import settings
from services.repositories.price_repo import PriceRepository
from services.websocket_manager import manager as ws_manager

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
import requests

class PlaywrightGoldScrapingService:
    def __init__(self, repo: PriceRepository):
        self.repo = repo
        self.browser: Optional[Browser] = None

    async def _setup_browser(self) -> Tuple[Browser, Page]:
        """Sets up and returns an active Playwright browser and page instance."""
        if not self.browser:
            p = await async_playwright().start()
            self.browser = await p.chromium.launch(headless=True)
        
        page = await self.browser.new_page()
        await page.set_viewport_size({"width": 1400, "height": 900})
        return self.browser, page
    
    async def _close_browser(self):
        if self.browser:
            await self.browser.close()
            print("Playwright Browser closed.")
            self.browser = None

    def _fetch_api_price(self) -> Optional[Tuple[str, str]]:
        try:
            headers = {'x-access-token': settings.API_KEY}
            full_url = f"{settings.API_BASE_URL}/{settings.API_SYMBOL}" 

            response = requests.get(full_url, headers=headers, timeout=10)
            response.raise_for_status() 
            data = response.json()
            
            if 'price' in data:
                price_value = data['price']
                return f"{price_value:.2f}", "GoldAPI.io"
            
            return None, None
        except Exception as e:
            print(f"GoldAPI Error: {e}")
            return None, None

    async def _fetch_scraping_price_async(self) -> Optional[Tuple[str, str]]:
        page: Optional[Page] = None
        try:
            _, page = await self._setup_browser()
            await page.goto(settings.FAILOVER_URL, wait_until="domcontentloaded", timeout=60000)
            
            try:
                consent_locator = page.locator("button:has-text('Accept'):visible, button:has-text('OK'):visible")
                await consent_locator.click(timeout=5000)
            except PlaywrightTimeoutError:
                pass 
            
            price_selector = settings.FAILOVER_CSS_SELECTOR
            price_locator = page.locator(price_selector)
            await price_locator.wait_for(state="visible", timeout=10000)
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

    def _get_current_price(self) -> Optional[Tuple[str, str]]:
        """Attempts API, then falls back to Scraping."""
        print("Start Playwright scraping...")
        try:
            loop = asyncio.get_event_loop()
            price, source = loop.run_until_complete(self._fetch_scraping_price_async())
            if price:
                print(f"SUCCESS: Fetched price from {source}.")
                return price, source
        except Exception as e:
            print(f"Playwright Scraping FAILED: {e}")
        print("CRITICAL: Both primary and failover sources failed.")
        return None, None

    async def run_scraper_loop_async(self, mongo_client: MongoClient):
        print("Dual-Source Async Scraper started.")
        while True:
            try:
                current_price, current_source = await self._fetch_scraping_price_async()

                if not current_price:
                    print("Warning: Failed to fetch price. Retrying...")
                    await asyncio.sleep(settings.SCRAPE_INTERVAL_SECONDS)
                    continue

                print(f"DEBUG: Price Check: '{current_price}' | Source: '{current_source}'")

                # Save price (wrap sync DB save in async)
                await asyncio.to_thread(self.repo.save_price, mongo_client, current_price, current_source)

                # Broadcast via WebSocket
                data_to_push = {
                    "price": current_price,
                    "source": current_source,
                    "timestamp": datetime.now().isoformat(),
                }
                await ws_manager.broadcast(data_to_push)

                await asyncio.sleep(settings.SCRAPE_INTERVAL_SECONDS)
            except Exception as e:
                print(f"Critical error in scraping loop: {e}")

        # Optional: cleanup browser (won't run in infinite loop)
        if self.browser:
            await self._close_browser()

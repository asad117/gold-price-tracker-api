# playwright_scraper_service.py (New File Name)

import time
import asyncio
import requests
from datetime import datetime
from typing import Optional, Awaitable, Any, Tuple
from pymongo import MongoClient

# --- New Playwright Imports ---
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

# --- Existing Imports ---
from config.settings import settings
from services.repositories.price_repo import PriceRepository
from services.websocket_manager import manager as ws_manager


# --- Utility Function Update (Simplified) ---
# We keep this helper, but it's crucial we only run the async Playwright part in the main thread.
def _run_async_in_thread(coro: Awaitable[Any], loop: asyncio.AbstractEventLoop) -> Any:
    """Safely runs an async coroutine on the main event loop from this worker thread."""
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


class PlaywrightGoldScrapingService:
    def __init__(self, repo: PriceRepository):
        self.repo = repo
        self.browser: Optional[Browser] = None
        self.last_price: Optional[str] = None
        self._loop = None # To store the running event loop

    # --- DRIVER SETUP (Replaced by Playwright Async Context) ---
    async def _setup_browser(self) -> Tuple[Browser, Page]:
        """Sets up and returns an active Playwright browser and page instance."""
        if not self.browser:
            # Launch browser (e.g., Chromium) in headless mode for deployment
            p = await async_playwright().start()
            self.browser = await p.chromium.launch(headless=True)
        
        page = await self.browser.new_page()
        
        # Set viewport for standard page rendering
        await page.set_viewport_size({"width": 1400, "height": 900})
        
        return self.browser, page
    
    # --- DRIVER SHUTDOWN (New async method to close the browser) ---
    async def _close_browser(self):
        if self.browser:
            await self.browser.close()
            print("Playwright Browser closed.")
            self.browser = None

    # --- SOURCE 1: API (Primary - NO CHANGE) ---
    def _fetch_api_price(self) -> Optional[Tuple[str, str]]:
        # This function remains synchronous as it uses the synchronous 'requests' library
        try:
            headers = {'x-access-token': settings.API_KEY}
            full_url = f"{settings.API_BASE_URL}/{settings.API_SYMBOL}" 

            response = requests.get(full_url, headers=headers, timeout=10)
            response.raise_for_status() 
            data = response.json()
            
            if 'price' in data:
                price_value = data['price']
                # Ensure the format is correct (matching Selenium's text output)
                return f"{price_value:.2f}", "GoldAPI.io" 
            
            print(f"Warning: GoldAPI response missing 'price' key. Full response: {data}")
            return None, None
        except requests.exceptions.RequestException as e:
            print(f"GoldAPI Request FAILED: {e}")
            return None, None
        except Exception as e:
            print(f"GoldAPI Parsing Error: {e}")
            return None, None
    
    # --- SOURCE 2: SCRAPING (Failover - REPLACED WITH PLAYWRIGHT) ---
    async def _fetch_scraping_price_async(self) -> Optional[Tuple[str, str]]:
        """Asynchronously scrapes price from the configured failover URL (IG.com) using Playwright."""
        page: Optional[Page] = None
        try:
            # 1. Setup browser and page
            _, page = await self._setup_browser()
            
            # 2. Navigate with a relaxed condition and increased timeout
            await page.goto(
                settings.FAILOVER_URL, 
                wait_until="domcontentloaded", 
                timeout=60000 
            )
            
            # 3. Handle Cookie/Popup Dismissal
            try:
                # Look for a common "Accept" button using text or role
                consent_locator = page.locator("button:has-text('Accept'):visible, button:has-text('OK'):visible")
                await consent_locator.click(timeout=5000)
            except PlaywrightTimeoutError:
                pass 
            
            # 4. Wait for the price element to be present and visible
            price_selector = settings.FAILOVER_CSS_SELECTOR # e.g., "div[data-field='BID']"
            price_locator = page.locator(price_selector)

            await price_locator.wait_for(state="visible", timeout=10000)
            
            # 5. Extract the price text
            current_price = await price_locator.inner_text()
            
            # Returns (price, source_name)
            return current_price.strip(), "IG.com (Playwright)"
        
        except PlaywrightTimeoutError as e:
            print(f"Scraping FAILED (Timeout): Selector '{settings.FAILOVER_CSS_SELECTOR}' not found or page took too long. {e}")
            return None, None
        except Exception as e:
            print(f"Scraping FAILED (Playwright Error): {e}")
            return None, None
        finally:
            if page:
                await page.close() # Close the page, but keep the browser open

    # --- MASTER FAILOVER METHOD (Synchronous wrapper) ---
    def _get_current_price(self) -> Optional[Tuple[str, str]]:
        """Attempts API, then falls back to Scraping (via async wrapper) if API fails."""
        
        # 1. Primary Source: API (Synchronous)
        price, source = self._fetch_api_price()
        if price:
            print(f"SUCCESS: Fetched price from {source}.")
            return price, source
        
        # 2. Failover Source: Scraping (Requires running async in the thread's loop)
        print("API failed. Falling back to Playwright scraping...")
        try:
            # Use the loop found during run_scraper_loop start
            coro = self._fetch_scraping_price_async()
            price, source = _run_async_in_thread(coro, self._loop)
            
            if price:
                print(f"SUCCESS: Fetched price from {source}.")
                return price, source
            
        except Exception as e:
            print(f"Playwright Scraping FAILED in thread: {e}")
        
        # 3. Both failed
        print("CRITICAL: Both primary and failover sources failed.")
        return None, None

    # --- MAIN LOOP (Modified for Playwright cleanup) ---
    def run_scraper_loop(self, mongo_client: MongoClient, loop: asyncio.AbstractEventLoop):
        self._loop = loop # Store the loop for use by the synchronous wrapper
        print("Dual-Source Service started.")
        try:
            while True:
                # 1. FETCH PRICE using failover logic
                current_price, current_source = self._get_current_price()

                if not current_price:
                    print("Warning: Failed to fetch price from any source. Retrying...")
                    time.sleep(settings.SCRAPE_INTERVAL_SECONDS)
                    continue

                print(
                    f"DEBUG: Price Check: '{current_price}' | Source: '{current_source}'"
                )

                # 2. SAVE to DB (Async call wrapped)
                _run_async_in_thread(
                    self.repo.save_price(mongo_client, current_price, current_source),
                    loop
                )

                # 3. BROADCAST via WebSocket (Async call wrapped)
                data_to_push = {
                    "price": current_price,
                    "source": current_source,
                    "timestamp": datetime.now().isoformat(),
                }

                _run_async_in_thread(
                    ws_manager.broadcast(data_to_push),
                    loop
                )

                time.sleep(settings.SCRAPE_INTERVAL_SECONDS)

        except Exception as e:
            print(f"Critical error in polling loop: {e}")

        finally:
            # Ensure Playwright browser is closed when the loop ends
            if self._loop and self.browser:
                # Need to run the async close method on the main loop
                print("Shutting down Playwright Browser...")
                _run_async_in_thread(self._close_browser(), self._loop)
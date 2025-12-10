# scraper_service.py

import asyncio
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
from typing import Optional

# --- Configuration ---
# Target URL: IG.com Gold Market
IG_URL: str = "https://www.ig.com/en/commodities/markets-commodities/gold"

# CSS Selector for the BID price
PRICE_CSS_SELECTOR: str = "div[data-field='BID']"

SCRAPE_INTERVAL_SECONDS: int = 4
INITIAL_WAIT_SECONDS: int = 8 

# --- Main Asynchronous Scraper Function ---

async def scrape_price_data(url: str, selector: str):
    """
    Launches a browser, navigates to IG.com, and continuously scrapes the BID price.
    """
    print(f"--- Launching Playwright for IG.com URL: {url} ---")
    
    async with async_playwright() as p:
        browser = None # Initialize browser variable outside try-block
        try:
            # Set headless=True for seamless, non-interactive backend execution
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # --- FIX 1 & 2: Relaxed Navigation and Increased Timeout ---
            await page.goto(
                url, 
                wait_until="domcontentloaded", # Changed from "networkidle" to a gentler state
                timeout=60000 # Increased timeout to 60 seconds (1 minute) for slow servers
            ) 
            print("Navigation succeeded (DOM Content Loaded).")
            
            # --- FIX 3: Robust Anti-Popup/Cookie Dismissal ---
            # Try to click the "Accept" button immediately. Use a generic text locator.
            try:
                # Use a combined selector for common consent buttons
                consent_locator = page.locator(
                    "button:has-text('Accept'):visible, button:has-text('OK'):visible, button[aria-label='Accept']"
                )
                await consent_locator.click(timeout=5000)
                print("Dismissed a potential cookie/popup barrier.")
            except PlaywrightTimeoutError:
                pass # If no popup found, that's fine, continue
                
            # --- Fixed Initial Wait for JavaScript Execution ---
            print(f"Waiting {INITIAL_WAIT_SECONDS} seconds for dynamic content to finish rendering...")
            await asyncio.sleep(INITIAL_WAIT_SECONDS)
                
            # --- Smart Wait for the target price element ---
            try:
                # Wait for the price element to be visible with an acceptable timeout
                await page.wait_for_selector(selector, timeout=10000) 
            except PlaywrightTimeoutError:
                print(f"CRITICAL ERROR: Timed out waiting for selector: {selector} after fixed delay.")
                print("Action needed: Verify the CSS selector is correct for the Gold page on IG.com.")
                return

            print("Price element found. Starting polling loop...")
            
            # --- Continuous Polling Loop ---
            while True:
                start_time = time.time()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                price_float: Optional[float] = None
                
                try:
                    price_locator = page.locator(selector)
                    price_text = await price_locator.inner_text()
                    
                    # Clean and validate the data
                    clean_price = price_text.strip().replace(',', '')
                    price_float = float(clean_price)
                    
                    print(f"[{timestamp}] SCRAPED PRICE (IG.com BID): {price_float:,.3f} USD")
                    
                except ValueError:
                    print(f"[{timestamp}] WARNING: Could not convert '{clean_price}' to float. Data format issue.")
                except Exception as e:
                    print(f"[{timestamp}] CRITICAL SCRAPING ERROR: An issue occurred during extraction. Error: {e}")
                    
                # Maintain the desired scrape interval
                elapsed_time = time.time() - start_time
                sleep_duration = max(0, SCRAPE_INTERVAL_SECONDS - elapsed_time)
                
                await asyncio.sleep(sleep_duration)

        except Exception as global_e:
            print(f"A fatal error occurred during Playwright launch or execution: {global_e}")
            print("This could indicate a network firewall or severe anti-bot rejection.")
        finally:
            if browser:
                await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(scrape_price_data(IG_URL, PRICE_CSS_SELECTOR))
    except KeyboardInterrupt:
        print("\nScraping service manually stopped.")
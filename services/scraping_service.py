import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import asyncio  
from typing import Optional
from pymongo import MongoClient
from config.settings import settings
from services.repositories.price_repo import PriceRepository
from services.websocket_manager import manager as ws_manager
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os 
import shutil
import sys
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import requests 

def _run_async_in_thread(coro, loop):
    """Safely runs an async coroutine on the main event loop from this worker thread."""
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

class GoldScrapingService:
    def __init__(self, repo: PriceRepository):
        self.repo = repo
        self.driver: webdriver.Chrome = None
        self.last_price: Optional[str] = None

    # def _setup_driver(self) -> webdriver.Chrome:
    #     """Configures and initializes the Selenium WebDriver."""
    #     print("Setting up WebDriver...")
    #     options = Options()
    #     # options.add_argument("--headless")
    #     options.add_argument('--headless=new')
    #     options.add_argument("--disable-gpu")
    #     options.add_argument("--no-sandbox")
    #       # 4. Shared Memory Fix (For stability)
    #     options.add_argument('--disable-dev-shm-usage')
    #     options.add_argument("--window-size=1920,1080")
    #     options.add_argument(
    #         "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")
       
    #     print("chrome versiion ",ChromeDriverManager().install())

    #     return webdriver.Chrome(
    #         service=Service(ChromeDriverManager().install()),
    #         options=options
    #     )



    # def _setup_driver(self) -> webdriver.Remote: 
    #     """Configures and initializes the Selenium WebDriver using Firefox/Geckodriver."""
    #     print("Setting up WebDriver (using Firefox/Geckodriver)...")
        
    #     # --- Firefox Options Setup ---
    #     options = FirefoxOptions()
    #     options.add_argument('--headless')

    #     # --- Dynamic Geckodriver Path ---
    #     driver_path = GeckoDriverManager().install()
    #     service = FirefoxService(executable_path=driver_path)
        
    #     print("Geckodriver path: ", driver_path)

    #     return webdriver.Firefox(
    #         service=service,
    #         options=options
    #     )
    

    # def _setup_driver(self) -> webdriver.Remote: 
    #     print("Setting up WebDriver (using Firefox/Geckodriver with stealth)...")
        
    #     options = FirefoxOptions()
    #     options.add_argument('--headless')

    #     # --- STEALTH PREFERENCES ---
    #     options.set_preference("dom.webdriver.enabled", False)
    #     options.set_preference("useAutomationExtension", False)
    #     options.set_preference("intl.accept_languages", "en-US, en")
    #     options.add_argument("--width=1920")
    #     options.add_argument("--height=1080")
    #     # ---------------------------

    #     driver_path = GeckoDriverManager().install()
    #     service = FirefoxService(executable_path=driver_path)
        
    #     print("Geckodriver path: ", driver_path)

    #     return webdriver.Firefox(
    #         service=service,
    #         options=options
    #     )

    # --- DRIVER SETUP (Only used for IG.com ) ---
    def _setup_driver(self) -> webdriver.Remote:
        print("Setting up Firefox WebDriver for failover...")
        options = FirefoxOptions()
        options.add_argument('--headless')
        driver_path = GeckoDriverManager().install()
        service = FirefoxService(executable_path=driver_path)
        return webdriver.Firefox(service=service, options=options)
    
        # --- SOURCE 1: API (Primary) ---
    def _fetch_api_price(self) -> Optional[tuple[str, str]]:
      
            try:
                headers = {
                    'x-access-token': settings.API_KEY
                }
                
                full_url = f"{settings.API_BASE_URL}/{settings.API_SYMBOL}" 

                response = requests.get(full_url, headers=headers, timeout=10)
                response.raise_for_status() 
                data = response.json()
                
                if 'price' in data:
                    price_value = data['price']
                    return f"{price_value:.2f}", "GoldAPI.io" 
                
                print(f"Warning: GoldAPI response missing 'price' key. Full response: {data}")
                return None, None

            except requests.exceptions.RequestException as e:
                print(f"GoldAPI Request FAILED: {e}")
                return None, None
            except Exception as e:
                print(f"GoldAPI Parsing Error: {e}")
                return None, None

            except requests.exceptions.RequestException as e:
                print(f"API Request FAILED: {e}")
                return None, None
    
    # --- SOURCE 2: SCRAPING (Failover) ---
    def _fetch_scraping_price(self) -> Optional[tuple[str, str]]:
        """Scrapes price from the configured failover URL (IG.com)."""
        if self.driver is None:
            self.driver = self._setup_driver()

        try:
            self.driver.get(settings.FAILOVER_URL)
            wait = WebDriverWait(self.driver, 5)
            price_selector = (By.CSS_SELECTOR, settings.FAILOVER_CSS_SELECTOR)
            
            wait.until(EC.presence_of_element_located(price_selector))
            price_element = self.driver.find_element(*price_selector)
            current_price = price_element.text.strip()
            
            # Returns (price, source_name)
            return current_price, "IG.com"
        
        except Exception as e:
            print(f"Scraping FAILED: {e}")
            # Do NOT quit the driver here; let the finally block handle it at shutdown.
            return None, None
    
     # --- MASTER FAILOVER METHOD ---
    def _get_current_price(self) -> Optional[tuple[str, str]]:
        """Attempts API, then falls back to Scraping if API fails."""
        
        price, source = self._fetch_scraping_price()
        if price:
            print(f"SUCCESS: Fetched price from {source}.")
            return price, source
        
        # 3. Both failed
        print("CRITICAL: Both primary and failover sources failed.")
        return None, None
    
    def run_scraper_loop(self, mongo_client: MongoClient, loop):
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
                    f"DEBUG: Price Check: '{current_price}' | Source: '{current_source}' | Last Price: '{self.last_price}'")

                # === PHASE 1: INITIALIZATION ===
                if self.last_price is None:
                    last_saved_data = _run_async_in_thread(
                        self.repo.get_last_price(mongo_client), loop
                    )
                    price_to_broadcast = current_price
                    timestamp_to_broadcast = datetime.now().isoformat()
                    
                    self.last_price = price_to_broadcast 
                    self.last_source = current_source 
                    data_to_push = {
                        "price": price_to_broadcast,
                        "source": current_source, 
                        "timestamp": timestamp_to_broadcast
                    }
                    _run_async_in_thread(ws_manager.broadcast(data_to_push), loop)
                    # print(f"DEBUG: *** INITIALIZATION COMPLETE. Source: {current_source} ***")

                    if last_saved_data is None or (current_price != last_saved_data.get('price')):
                        _run_async_in_thread(self.repo.save_price(
                            mongo_client, current_price, current_source), loop) 

                # === PHASE 2: CHANGE DETECTION ===
                # Check for price change OR if the source changed while the price stayed the same (important for tracking)
                elif current_price != self.last_price or current_source != self.last_source:

                    print(f"DEBUG: *** PRICE OR SOURCE CHANGE DETECTED: {current_price} from {current_source} ***")

                    _run_async_in_thread(self.repo.save_price(
                        mongo_client, current_price, current_source), loop) 

                    data_to_push = {
                        "price": current_price,
                        "source": current_source, 
                        "timestamp": datetime.now().isoformat()
                    }
                    _run_async_in_thread(ws_manager.broadcast(data_to_push), loop)

                    self.last_price = current_price
                    self.last_source = current_source # NEW
                    print(f"Update: Pushed new price: {current_price} from {current_source}")
                    data_to_push = {
                        "price": current_price,
                        "source": current_source, 
                        "timestamp": datetime.now().isoformat()
                    }
                time.sleep(settings.SCRAPE_INTERVAL_SECONDS)

        except Exception as e:
            print(f"Critical error in polling loop: {e}")

        finally:
            if self.driver:
                self.driver.quit()
                print("WebDriver closed.")

from pydantic_settings import BaseSettings, SettingsConfigDict 
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    API_KEY: str
    MONGO_URI: str
    SECRET_KEY: str 
    
    # --- MongoDB Settings ---
    MONGO_DB: str = "price_db"
    MONGO_COLLECTION: str = "scraped_data"

    # --- API SETTINGS (Primary Source) ---
    API_BASE_URL: str = "https://www.goldapi.io/api" 
    API_SYMBOL: str = "XAU/USD"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    FAILOVER_URL: str = "https://www.ig.com/en/commodities/markets-commodities/gold"
    FAILOVER_CSS_SELECTOR: str = "div[data-field='BID']"
    
    TARGET_URL: str = "https://www.tradingview.com/symbols/GOLD/?exchange=TVC"
    SCRAPE_INTERVAL_SECONDS: int = 2
    PRICE_CSS_SELECTOR: str = "span[data-qa-id='symbol-last-value']"
    API_KEY_HEADER: str = "X-API-Key"

settings = Settings()
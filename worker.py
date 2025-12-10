# worker.py
import asyncio
import os
from core.database import connect_to_mongo, get_mongo_client, close_mongo_connection
from services.playwright_scraper_service import PlaywrightGoldScrapingService as GoldScrapingService
from services.repositories.price_repo import PriceRepository

async def run_worker():
    # connect to DB
    await connect_to_mongo()
    mongo_client = get_mongo_client()
    price_repo = PriceRepository()
    scraper = GoldScrapingService(repo=price_repo)

    # If your scraper exposes run_scraper_loop_async(mongo_client) like in main.py:
    await scraper.run_scraper_loop_async(mongo_client)

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("Worker stopped")
    finally:
        # best-effort to close DB
        try:
            asyncio.run(close_mongo_connection())
        except Exception:
            pass

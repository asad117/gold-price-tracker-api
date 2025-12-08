from config.settings import settings
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any, Optional
# from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

class PriceDocument(BaseModel):
    price: str
    source: str = "N/A" # NEW: Add source field
    unit: str = "ounce"
    timestamp: datetime = datetime.now()



class PriceRepository:

    def __init__(self):
        self.collection_name = settings.MONGO_COLLECTION

    async def save_price(self, client: MongoClient, price_value: str, source: str) -> str:
        """Saves a new price record to MongoDB, including the source."""
        db = client[settings.MONGO_DB]
        collection = db.get_collection(self.collection_name)
        doc = PriceDocument(price=price_value, source=source).model_dump()

        result = await collection.insert_one(doc)
        return str(result.inserted_id)

    async def get_last_price(self, client: MongoClient) -> Optional[Dict[str, Any]]:
        """Fetches the most recent price document from the database."""
        # db = client.get_database()
        db = client[settings.MONGO_DB]
        collection = db.get_collection(self.collection_name)
        # print(f"DEBUG: Fetching collection: {collection}")

        last_doc = await collection.find({}) \
            .sort("timestamp", -1) \
            .limit(1) \
            .to_list(length=1)
        return last_doc[0] if last_doc else None

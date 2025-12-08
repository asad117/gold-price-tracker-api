from pymongo import MongoClient
from config.settings import settings
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

# client: MongoClient = None
client: Optional[AsyncIOMotorClient] = None
def get_mongo_client() -> AsyncIOMotorClient:
    """Returns the initialized MongoDB client."""
    global client
    if client is None:
        raise ConnectionError("MongoDB client not initialized.")
    return client

async def connect_to_mongo():
    """Initializes the MongoDB connection pool."""
    global client
    print("Connecting to MongoDB...")
    try:
        # client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000) 
        
        await client.admin.command('ping')
        print("✅ MongoDB connection established.")
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        raise

async def close_mongo_connection():
    """Closes the MongoDB connection."""
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")
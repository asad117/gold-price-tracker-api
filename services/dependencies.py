from typing import Annotated
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient 
from config.settings import Settings 
from services.repositories.user_repo import UserRepository
from core.database import get_mongo_client 


_settings: Settings | None = None

def get_settings() -> Settings:
    """Provides the application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

async def get_db():
    """Returns the specific database instance (e.g., 'price_db')."""
    client = get_mongo_client()
    return client.price_db 


async def get_user_repo_dependency(
    db: Annotated[AsyncIOMotorClient, Depends(get_db)]
) -> UserRepository:
    """Provides a UserRepository instance tied to the database."""
    return UserRepository(db=db)
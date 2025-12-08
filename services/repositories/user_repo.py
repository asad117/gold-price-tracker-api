from bson import ObjectId
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings 
from models.user import UserInDB, UserCreate, UserPublic, UserUpdate, UserRole
from datetime import datetime

class UserRepository:
    def __init__(self, mongo_client: AsyncIOMotorClient):
        self.client = mongo_client
        self.db = self.client.get_database(settings.MONGO_DB)
        self.collection = self.db.get_collection("users")
        
    async def create_user(self, user_data: UserCreate, role: UserRole = 'user') -> UserPublic:
        from security.auth import get_password_hash 
        
        # 1. Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # 2. Create DB document
        user_doc = UserInDB(
            **user_data.model_dump(exclude={'password'}),
            hashed_password=hashed_password,
            role=role,
            created_at=datetime.utcnow()
        )
        
        # 3. Insert document
        user_dict_to_insert = user_doc.model_dump(
            by_alias=True, 
            exclude_none=True  
        )
        
        result = await self.collection.insert_one(user_dict_to_insert)
        
        # 4. Update the Pydantic model with the generated ID
        user_doc.id = str(result.inserted_id)
        
        # 5. Return the public view
        return UserPublic(**user_doc.model_dump(by_alias=True))

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        doc = await self.collection.find_one({"email": email})
        if doc:
            return UserInDB(**doc)
        return None

    # Admin functions (CRUD)
    async def get_all_users(self) -> List[UserPublic]:
        users_raw = await self.collection.find().to_list(1000)
        
        users_public = []
        for user_doc in users_raw:
            if '_id' in user_doc:
                user_doc['id'] = str(user_doc['_id'])
                del user_doc['_id'] 
            try:
                users_public.append(UserPublic.model_validate(user_doc))
            except Exception as e:
                print(f"Skipping user due to validation error: {e}")
                continue
                
        return users_public

    async def get_user_by_id(self, user_id: str) -> Optional[UserPublic]:
        if not ObjectId.is_valid(user_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        if doc:
            return UserPublic(**doc)
        return None

    async def update_user(self, user_id: str, update_data: UserUpdate) -> Optional[UserPublic]:
        if not ObjectId.is_valid(user_id):
            return None
            
        update_doc = update_data.model_dump(exclude_none=True)
        if not update_doc:
            return await self.get_user_by_id(user_id)
        
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_doc}
        )
        if result.modified_count == 1:
            return await self.get_user_by_id(user_id)
        return None

    async def delete_user(self, user_id: str) -> bool:
        if not ObjectId.is_valid(user_id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count == 1
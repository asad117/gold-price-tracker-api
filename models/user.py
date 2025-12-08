from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field,ConfigDict
from enum import Enum
from bson import ObjectId
# UserRole = Literal['user', 'admin']

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserRole(str, Enum):
    USER = "user" 
    ADMIN = "admin"

class UserCreate(BaseModel):
    """Schema for user registration request (input model)."""
    full_name: str = Field(min_length=3)
    email: EmailStr
    password: str = Field(min_length=8)
    phone: str
    company: str
    address: str
    country: str
    account_type: Literal['individual', 'corporate'] = 'individual' 


class UserPublic(BaseModel):
    id: Optional[str] = Field(None, alias="_id") 
    email: str
    role: str
    full_name: Optional[str] = None
    created_at: datetime
    company: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    account_type: Optional[str] = None

    class Config:
        populate_by_name = True

class UserUpdate(BaseModel):
    """Schema for updating user data (PATCH/PUT request)."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    account_type: Optional[Literal['individual', 'corporate']] = None


# --- MongoDB Schema (Internal Model) ---
class UserInDB(BaseModel):
    id: Optional[ObjectId] = Field(alias="_id", default=None) 
    full_name: str
    email: str
    hashed_password: str
    phone: str
    role: str
    
    created_at: datetime 
    company: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    account_type: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda dt: dt.isoformat() 
        }
    )
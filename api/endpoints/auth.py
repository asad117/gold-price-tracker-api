from typing import Annotated
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from models.user import UserCreate, UserPublic, UserRole 
from services.repositories.user_repo import UserRepository 
from security.auth import (
    verify_password, 
    create_access_token,
    get_user_repo_dependency 
)
from config.settings import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    user_repo: Annotated[UserRepository, Depends(get_user_repo_dependency)] 
):
    """Register a new standard 'user'."""
    existing_user = await user_repo.get_user_by_email(user_data.email)
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    new_user = await user_repo.create_user(user_data, role=UserRole.USER.value)
    return new_user

@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repo: Annotated[UserRepository, Depends(get_user_repo_dependency)] 
):
    """Authenticate a user and return an access token."""
    # Use the injected user_repo object
    user_doc = await user_repo.get_user_by_email(form_data.username) 
    
    if not user_doc or not verify_password(form_data.password, user_doc.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_doc.email, "role": user_doc.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_email": user_doc.email,
        "user_role": user_doc.role,
        "user_full_name": user_doc.full_name,
    }
from fastapi import APIRouter, Depends
from models.user import UserPublic
from security.auth import get_current_user 

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user
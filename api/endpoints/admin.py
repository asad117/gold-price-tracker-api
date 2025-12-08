from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path
from pydantic import Field 
from fastapi import APIRouter, Depends, HTTPException, status
from models.user import UserCreate, UserPublic, UserRole,UserUpdate
from services.repositories.user_repo import UserRepository
from services.repositories.user_repo import UserRepository 
from security.auth import (
    get_current_active_admin, # The dependency to ensure the user is an admin
    get_user_repo_dependency # The dependency to inject the UserRepository
)

router = APIRouter(
    prefix="/admin/users", 
    tags=["Admin"], 
    dependencies=[Depends(get_current_active_admin)] 
)

@router.get("/", response_model=List[UserPublic], summary="List all users")
async def list_users(
    user_repo: Annotated[UserRepository, Depends(get_user_repo_dependency)]
):
    return await user_repo.get_all_users()


@router.get("/{user_id}", response_model=UserPublic, summary="Get user by ID")
async def get_user(
    user_id: Annotated[str, Path(description="The ID of the user to retrieve")],
    user_repo: Annotated[UserRepository, Depends(get_user_repo_dependency)]
):
    user = await user_repo.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# --- UPDATE & DELETE OPERATIONS ---
@router.patch("/{user_id}", response_model=UserPublic, summary="Update user details")
async def update_user(
    user_id: Annotated[str, Path(description="The ID of the user to update")],
    user_update: UserUpdate,
    user_repo: Annotated[UserRepository, Depends(get_user_repo_dependency)]
):
    updated_user = await user_repo.update_user(user_id, user_update)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or nothing to update")
    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user")
async def delete_user(
    user_id: Annotated[str, Path(description="The ID of the user to delete")],
    user_repo: Annotated[UserRepository, Depends(get_user_repo_dependency)]
):
    success = await user_repo.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message": "User deleted successfully"}

# router = APIRouter(prefix="/admin", tags=["Admin"])

# # Assuming UserCreate is the same schema for admin registration
# @router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
# async def register_admin_user(
#     user_data: UserCreate,
#     user_repo: Annotated[UserRepository, Depends(get_user_repo_dependency)],
#     settings: Annotated[dict, Depends(get_settings)] # Replace dict with your Settings type
# ):
#     # SECURITY STEP 1: Implement a check here, perhaps a header key 
#     # to prevent public access. For simplicity, we skip it here, but it MUST be done.

#     existing_user = await user_repo.get_user_by_email(user_data.email)
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, 
#             detail="Email already registered"
#         )
    
#     # SECURITY STEP 2: Explicitly assign the ADMIN role
#     # Assuming UserRole.ADMIN.value is the string "admin"
#     new_user = await user_repo.create_user(user_data, role=UserRole.ADMIN.value)
    
#     return new_user
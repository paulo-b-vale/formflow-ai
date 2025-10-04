# app/routers/user_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import user_service
from app.dependencies.auth import get_current_active_user, require_admin
from app.core.exceptions import NotFoundError, ValidationError, PermissionError

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_active_user)):
    """Get information about the currently authenticated user."""
    return current_user

@router.put("/me", response_model=UserResponse, response_model_by_alias=False)
async def update_users_me(
    user_update: UserUpdate,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Update the current user's information."""
    try:
        return await user_service.update_user(str(current_user.id), user_update, current_user.model_dump())
    except (ValidationError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/", response_model=List[UserResponse], dependencies=[Depends(require_admin)], response_model_by_alias=False)
async def read_all_users(skip: int = 0, limit: int = 100):
    """Retrieve all users (admin only)."""
    return await user_service.get_all_users(skip=skip, limit=limit, role=None)
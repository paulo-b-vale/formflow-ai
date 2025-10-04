# app/services/user_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
import logging

from app.services.base_service import BaseService
from app.models.enums import UserRole
from app.schemas.user import UserUpdate, UserResponse
from app.core.security import get_password_hash
from app.core.exceptions import NotFoundError, ValidationError, PermissionError

logger = logging.getLogger(__name__)

class UserService(BaseService):
    """Handles all CRUD (Create, Read, Update, Delete) operations for users."""

    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        if not ObjectId.is_valid(user_id):
            return None
        user_data = await self.db.users.find_one({"_id": ObjectId(user_id)})
        return UserResponse.model_validate(user_data) if user_data else None

    async def get_all_users(self, skip: int, limit: int, role: Optional[UserRole]) -> List[UserResponse]:
        query = {}
        if role:
            query["role"] = role.value
        
        cursor = self.db.users.find(query).skip(skip).limit(limit)
        users = await cursor.to_list(length=limit)
        return [UserResponse.model_validate(user) for user in users]

    async def update_user(self, user_id: str, user_update: UserUpdate, current_user: Dict[str, Any]) -> UserResponse:
        if not ObjectId.is_valid(user_id):
            raise ValidationError("Invalid user ID.")

        # Permission Check: Admin can edit anyone, users can only edit themselves.
        if current_user["role"] != UserRole.ADMIN.value and current_user["id"] != user_id:
            raise PermissionError("You do not have permission to update this user.")

        update_data = user_update.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No update data provided.")

        # Hash password if it's being updated
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        # Check for email uniqueness if email is being changed
        if "email" in update_data:
            existing_user = await self.db.users.find_one(
                {"email": update_data["email"], "_id": {"$ne": ObjectId(user_id)}}
            )
            if existing_user:
                raise ValidationError("This email address is already in use.")
        
        update_data["updated_at"] = datetime.utcnow()
        result = await self.db.users.update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_data}
        )

        if result.matched_count == 0:
            raise NotFoundError("User not found.")

        updated_user = await self.get_user_by_id(user_id)
        logger.info(f"User {user_id} updated by {current_user['id']}")
        return updated_user

    async def delete_user(self, user_id: str, current_user: Dict[str, Any]) -> bool:
        """Performs a soft delete by deactivating the user."""
        if not ObjectId.is_valid(user_id):
            raise ValidationError("Invalid user ID.")
            
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can delete users.")
            
        if current_user["id"] == user_id:
            raise ValidationError("Administrators cannot delete their own accounts.")

        result = await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )

        if result.matched_count == 0:
            raise NotFoundError("User not found.")
            
        logger.info(f"User {user_id} deactivated by {current_user['id']}")
        return True

# Create a single instance of the service
user_service = UserService()
# app/services/auth_service.py
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from bson import ObjectId

from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth import Token, LoginResponse
from app.schemas.user import UserCreate, UserResponse
from app.core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, verify_token
)
from app.core.exceptions import AuthenticationError, ValidationError
from app.services.base_service import BaseService
from app.database import get_redis
from app.config.settings import settings

logger = logging.getLogger(__name__)

class AuthService(BaseService):
    """Handles all authentication and user registration logic."""
    
    def __init__(self):
        super().__init__()
        self.redis = None

    async def initialize(self):
        """Initialize the service by getting Redis connection."""
        await super().initialize()
        try:
            self.redis = await get_redis()
            logger.info("Redis connection established for AuthService.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Token revocation will not be available.")
            self.redis = None

    async def register_user(self, user_create: UserCreate) -> UserResponse:
        """Registers a new user, hashes their password, and saves them to the database."""
        # Build the query to check for existing users
        query_conditions = [{"email": user_create.email}]
        if user_create.phone_number is not None:
            query_conditions.append({"phone_number": user_create.phone_number})
        
        if await self.db.users.find_one({"$or": query_conditions}):
            raise ValidationError("User with this email or phone number already exists.")

        hashed_password = get_password_hash(user_create.password)
        
        user_model = User(
            **user_create.model_dump(exclude={"password", "role"}),  # Exclude role to prevent privilege escalation
            role=UserRole.USER,  # Always set role to USER for new registrations
            hashed_password=hashed_password
        )
        
        user_dict = user_model.model_dump(by_alias=True)
        # Pydantic v2 with `by_alias=True` handles `id` -> `_id` mapping.
        # We must remove the default `_id` so MongoDB can create its own.
        del user_dict['_id']
        
        # Remove phone_number from the dict if it's None to avoid sparse index issues
        if user_dict.get('phone_number') is None:
            del user_dict['phone_number']
            
        result = await self.db.users.insert_one(user_dict)
        created_user = await self.db.users.find_one({"_id": result.inserted_id})
        
        logger.info(f"User registered successfully: {created_user['email']}")
        return UserResponse.model_validate(created_user)

    async def authenticate_user(self, identifier: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticates a user by checking email or phone number and password. Returns user data if successful."""
        # First try email
        user_data = await self.db.users.find_one({"email": identifier})
        # If not found by email, try phone number
        if not user_data:
            user_data = await self.db.users.find_one({"phone_number": identifier})
        
        if not user_data or not verify_password(password, user_data["hashed_password"]):
            logger.warning(f"Authentication failed for user: {identifier}")
            return None

        if not user_data.get("is_active", True):
            logger.warning(f"Authentication failed: User inactive - {identifier}")
            raise AuthenticationError("This user account is inactive.")
            
        return user_data

    async def _is_token_revoked(self, jti: str) -> bool:
        """Check if a token has been revoked."""
        if not self.redis:
            return False
        return bool(await self.redis.exists(f"revoked_token:{jti}"))

    async def create_user_tokens(self, user_data: Dict[str, Any]) -> Token:
        """Creates and stores access and refresh tokens for a given user."""
        user_id_str = str(user_data["_id"])
        token_data = {
            "sub": user_data["email"], 
            "user_id": user_id_str, 
            "role": user_data.get("role", "user")
        }
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
        
        # Store refresh token in Redis for validation (optional)
        if self.redis:
            try:
                # Decode the refresh token to get its payload
                refresh_payload = verify_token(refresh_token, "refresh")
                # Store the refresh token with expiration
                await self.redis.setex(
                    f"refresh_token:{refresh_payload.jti}",
                    timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                    user_id_str
                )
            except Exception as e:
                logger.warning(f"Failed to store refresh token in Redis: {e}")
        
        return Token(access_token=access_token, refresh_token=refresh_token)

    async def login(self, identifier: str, password: str) -> LoginResponse:
        """Handles the complete user login process with email or phone number."""
        user_data = await self.authenticate_user(identifier, password)
        if not user_data:
            raise AuthenticationError("Invalid email, phone number or password.")
            
        tokens = await self.create_user_tokens(user_data)
        
        await self.db.users.update_one(
            {"_id": user_data["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        user_response_data = UserResponse.model_validate(user_data)
        
        return LoginResponse(user=user_response_data, tokens=tokens)

    async def phone_login(self, phone_number: str, password: str) -> LoginResponse:
        """Handles the complete user login process using phone number."""
        user_data = await self.authenticate_user(phone_number, password)
        if not user_data:
            raise AuthenticationError("Invalid phone number or password.")
            
        tokens = await self.create_user_tokens(user_data)
        
        await self.db.users.update_one(
            {"_id": user_data["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        user_response_data = UserResponse.model_validate(user_data)
        
        return LoginResponse(user=user_response_data, tokens=tokens)

    async def refresh_access_token(self, refresh_token: str) -> Token:
        """Refreshes an access token using a valid refresh token."""
        try:
            payload = verify_token(refresh_token, "refresh")
            
            # Check if refresh token has been revoked (if Redis is available)
            if self.redis:
                is_revoked = await self._is_token_revoked(payload.jti)
                if is_revoked:
                    raise AuthenticationError("Refresh token has been revoked.")
            
            user_data = await self.db.users.find_one({"email": payload.sub})
            if not user_data or not user_data.get("is_active"):
                raise AuthenticationError("User not found or is inactive.")

            new_tokens = await self.create_user_tokens(user_data)
            return new_tokens
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise AuthenticationError(f"Token refresh failed: {e}")

    async def logout(self, refresh_token: str) -> bool:
        """
        Revokes a refresh token, effectively logging out the user.
        Returns True if successful, False otherwise.
        """
        if not self.redis:
            logger.warning("Redis not available. Logout functionality is limited.")
            return False
            
        try:
            # Verify the refresh token to get its payload
            payload = verify_token(refresh_token, "refresh")
            
            # Add the token to the revoked tokens set in Redis
            await self.redis.setex(
                f"revoked_token:{payload.jti}",
                timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                "revoked"
            )
            
            logger.info(f"Refresh token {payload.jti} has been revoked.")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke refresh token: {e}")
            return False

# Create a single instance of the service
auth_service = AuthService()
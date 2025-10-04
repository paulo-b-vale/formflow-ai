# app/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from app.core.security import verify_token
from app.services.user_service import user_service
from app.schemas.user import UserResponse
from app.models.enums import UserRole
from app.core.exceptions import AuthenticationError, PermissionError
from app.database import get_redis
from app.config.settings import settings

# This tells FastAPI where the client should go to get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """
    Dependency to get the current user from a JWT token.
    
    Decodes the token, validates its payload, and fetches the user from the database.
    Also checks if the token has been revoked.
    """
    try:
        payload = verify_token(token, "access")
        
        # Check if token has been revoked (if Redis is available)
        try:
            redis = await get_redis()
            # Get the token's unique identifier (jti)
            decoded_payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            jti = decoded_payload.get("jti")
            if jti and await redis.exists(f"revoked_token:{jti}"):
                raise AuthenticationError("Token has been revoked.")
        except Exception:
            # If Redis is not available or there's an error, we continue without revocation check
            pass
        
        user = await user_service.get_user_by_id(payload.user_id)
        if not user:
            raise AuthenticationError("User not found.")
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Dependency that builds on get_current_user to ensure the user is active.
    This is the one you'll use most often in your endpoints.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user.")
    return current_user

# --- Role-based Authorization Dependencies ---

def require_role(required_roles: list[UserRole]):
    """
    A factory for creating role-based dependency checkers.
    """
    async def role_checker(
        current_user: UserResponse = Depends(get_current_active_user)
    ) -> UserResponse:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join([role.value for role in required_roles])}."
            )
        return current_user
    return role_checker

# Specific role dependencies for easy use in routers
require_admin = require_role([UserRole.ADMIN])
require_professional = require_role([UserRole.PROFESSIONAL])
require_admin_or_professional = require_role([UserRole.ADMIN, UserRole.PROFESSIONAL])
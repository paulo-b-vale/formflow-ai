# app/routers/auth_router.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.auth import LoginResponse, RefreshTokenRequest, Token, LogoutRequest, PhoneLoginRequest
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import auth_service
from app.core.exceptions import AuthenticationError, ValidationError

# Get the logger
logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def register(user_create: UserCreate):
    """Register a new user."""
    try:
        return await auth_service.register_user(user_create)
    except ValidationError as e:
        # This is for expected validation errors, like a duplicate email
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # --- THIS IS THE NEW DEBUGGING BLOCK ---
        # It catches any unexpected error that causes the 500 status
        logger.error(f"An unexpected error occurred during registration: {e}", exc_info=True)
        # We raise a new HTTPException that includes the details of the original error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {type(e).__name__} - {e}"
        )

@router.post("/login", response_model=LoginResponse, response_model_by_alias=False)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user and return tokens."""
    try:
        return await auth_service.login(form_data.username, form_data.password)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {type(e).__name__} - {e}"
        )

@router.post("/phone-login", response_model=LoginResponse, response_model_by_alias=False)
async def phone_login(phone_login_request: PhoneLoginRequest):
    """Login user using phone number and password and return tokens."""
    try:
        return await auth_service.phone_login(phone_login_request.phone_number, phone_login_request.password)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during phone login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {type(e).__name__} - {e}"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token."""
    try:
        return await auth_service.refresh_access_token(request.refresh_token)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post("/logout", response_model=dict)
async def logout(request: LogoutRequest):
    """Logout user by revoking refresh token."""
    try:
        success = await auth_service.logout(request.refresh_token)
        if success:
            return {"message": "Successfully logged out."}
        else:
            return {"message": "Logout processed, but token revocation may not be persistent."}
    except Exception as e:
        logger.error(f"An unexpected error occurred during logout: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {type(e).__name__} - {e}"
        )
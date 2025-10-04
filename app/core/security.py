# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError as PydanticValidationError

from app.config.settings import settings
from app.core.exceptions import AuthenticationError
from app.schemas.auth import TokenPayload

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer Scheme
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against its hashed version."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a new access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Generate a unique ID for the token (jti)
    import uuid
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "token_type": "access", "jti": jti})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Creates a new refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    # Generate a unique ID for the token (jti)
    import uuid
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "token_type": "refresh", "jti": jti})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> TokenPayload:
    """
    Decodes and verifies a JWT token.
    
    Raises:
        AuthenticationError: If the token is invalid, expired, or has the wrong type.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if payload.get("token_type") != token_type:
            raise AuthenticationError(message=f"Invalid token type: expected '{token_type}'")

        # Validate payload with Pydantic model
        token_data = TokenPayload(**payload)
        
    except (JWTError, PydanticValidationError) as e:
        raise AuthenticationError(message=f"Could not validate credentials: {e}")
        
    return token_data
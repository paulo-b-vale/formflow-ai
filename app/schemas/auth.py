# app.schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Union

from app.schemas.user import UserResponse

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Union[EmailStr, str]
    user_id: str
    role: str
    exp: int
    token_type: str
    jti: Optional[str] = None  # JWT ID for token revocation

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PhoneLoginRequest(BaseModel):
    phone_number: str
    password: str

class LoginResponse(BaseModel):
    user: UserResponse
    tokens: Token

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str
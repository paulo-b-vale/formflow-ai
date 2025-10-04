# app/models/user.py
from pydantic import Field, EmailStr
from typing import Optional
from .enums import UserRole
from .file import MongoBaseModel

class User(MongoBaseModel):
    """Represents a user in the system."""
    name: str = Field(...)
    email: EmailStr = Field(...)
    phone_number: Optional[str] = Field(None)
    
    hashed_password: str = Field(...)
    role: UserRole = Field(default=UserRole.USER)
    
    is_active: bool = Field(True)
    last_login: Optional[str] = Field(None)
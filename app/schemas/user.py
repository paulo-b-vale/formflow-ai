# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.enums import UserRole
from app.models.file import PyObjectId # <-- Import PyObjectId

class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True

class UserCreate(UserBase):
    password: str

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

    @field_validator('phone_number')
    def validate_phone_number(cls, v):
        if v and not v.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError('Phone number must contain only digits, optionally with +, -, or spaces')
        if v and len(v.replace("+", "").replace("-", "").replace(" ", "")) < 10:
            raise ValueError('Phone number must be at least 10 digits long')
        return v

class UserUpdate(BaseModel):
    # ... (no changes in this class)
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: PyObjectId = Field(alias="_id") # <-- THE FIX: Changed from str to PyObjectId
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
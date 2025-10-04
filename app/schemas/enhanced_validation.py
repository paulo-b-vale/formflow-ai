"""
Enhanced validation schemas using Pydantic v2.

This module provides comprehensive validation schemas for all API endpoints
with detailed error messages and type checking.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, validator, ConfigDict
from bson import ObjectId


class PyObjectId(str):
    """Custom ObjectId type for Pydantic v2."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, handler):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )


# User Validation Schemas
class UserCreateSchema(BaseSchema):
    """Schema for user creation."""

    name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (min 8 characters)"
    )
    role: str = Field(default="user", description="User role")

    @validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate user role."""
        allowed_roles = ["user", "admin", "professional"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class UserUpdateSchema(BaseSchema):
    """Schema for user updates."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate user role."""
        if v is not None:
            allowed_roles = ["user", "admin", "professional"]
            if v not in allowed_roles:
                raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class UserResponseSchema(BaseSchema):
    """Schema for user responses."""

    id: PyObjectId = Field(alias="_id")
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


# Form Field Validation Schemas
class FormFieldSchema(BaseSchema):
    """Schema for form field definitions."""

    field_id: str = Field(..., min_length=1, max_length=50, description="Unique field identifier")
    label: str = Field(..., min_length=1, max_length=200, description="Field display label")
    field_type: str = Field(..., description="Field type")
    required: bool = Field(default=False, description="Whether field is required")
    description: Optional[str] = Field(None, max_length=500, description="Field description")
    placeholder: Optional[str] = Field(None, max_length=200, description="Field placeholder")
    validation_pattern: Optional[str] = Field(None, description="Regex validation pattern")
    min_length: Optional[int] = Field(None, ge=0, description="Minimum length")
    max_length: Optional[int] = Field(None, ge=1, description="Maximum length")
    options: Optional[List[str]] = Field(None, description="Options for select fields")
    default_value: Optional[str] = Field(None, description="Default value")

    @validator("field_type")
    @classmethod
    def validate_field_type(cls, v):
        """Validate field type."""
        allowed_types = [
            "text", "textarea", "email", "phone", "number", "currency",
            "date", "url", "select", "radio", "checkbox", "file"
        ]
        if v not in allowed_types:
            raise ValueError(f"Field type must be one of: {', '.join(allowed_types)}")
        return v

    @validator("field_id")
    @classmethod
    def validate_field_id(cls, v):
        """Validate field ID format."""
        import re
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError("Field ID must start with a letter and contain only letters, numbers, and underscores")
        return v


# Form Template Validation Schemas
class FormTemplateCreateSchema(BaseSchema):
    """Schema for creating form templates."""

    title: str = Field(..., min_length=1, max_length=200, description="Form title")
    description: Optional[str] = Field(None, max_length=1000, description="Form description")
    context_id: Optional[PyObjectId] = Field(None, description="Associated context ID")
    status: str = Field(default="draft", description="Form status")
    fields: List[FormFieldSchema] = Field(..., min_items=1, description="Form fields")
    tags: Optional[List[str]] = Field(None, description="Form tags")

    @validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate form status."""
        allowed_statuses = ["draft", "active", "archived"]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

    @validator("fields")
    @classmethod
    def validate_fields(cls, v):
        """Validate form fields."""
        field_ids = [field.field_id for field in v]
        if len(field_ids) != len(set(field_ids)):
            raise ValueError("Field IDs must be unique within a form")
        return v


class FormTemplateUpdateSchema(BaseSchema):
    """Schema for updating form templates."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = None
    fields: Optional[List[FormFieldSchema]] = None
    tags: Optional[List[str]] = None

    @validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate form status."""
        if v is not None:
            allowed_statuses = ["draft", "active", "archived"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v


# Form Response Validation Schemas
class FormResponseCreateSchema(BaseSchema):
    """Schema for creating form responses."""

    form_template_id: PyObjectId = Field(..., description="Form template ID")
    responses: Dict[str, Any] = Field(..., description="Field responses")

    @validator("responses")
    @classmethod
    def validate_responses(cls, v):
        """Validate form responses."""
        if not v:
            raise ValueError("Responses cannot be empty")
        return v


class FormResponseUpdateSchema(BaseSchema):
    """Schema for updating form responses."""

    responses: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

    @validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate response status."""
        if v is not None:
            allowed_statuses = ["draft", "submitted", "approved", "rejected"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v


# Context Validation Schemas
class ContextCreateSchema(BaseSchema):
    """Schema for creating contexts."""

    title: str = Field(..., min_length=1, max_length=200, description="Context title")
    description: Optional[str] = Field(None, max_length=1000, description="Context description")
    context_type: str = Field(..., description="Context type")
    assigned_users: Optional[List[PyObjectId]] = Field(default=[], description="Assigned user IDs")
    assigned_professionals: Optional[List[PyObjectId]] = Field(default=[], description="Assigned professional IDs")

    @validator("context_type")
    @classmethod
    def validate_context_type(cls, v):
        """Validate context type."""
        allowed_types = ["construction", "legal", "medical", "education", "business", "other"]
        if v not in allowed_types:
            raise ValueError(f"Context type must be one of: {', '.join(allowed_types)}")
        return v


# File Upload Validation Schemas
class FileUploadSchema(BaseSchema):
    """Schema for file uploads."""

    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    file_size: int = Field(..., gt=0, le=50*1024*1024, description="File size in bytes (max 50MB)")

    @validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        """Validate file content type."""
        allowed_types = [
            "image/jpeg", "image/png", "image/gif", "image/webp",
            "application/pdf", "text/plain", "text/csv",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ]
        if v not in allowed_types:
            raise ValueError(f"Content type not allowed: {v}")
        return v


# Conversation Validation Schemas
class ConversationMessageSchema(BaseSchema):
    """Schema for conversation messages."""

    session_id: str = Field(..., min_length=1, max_length=100, description="Session ID")
    user_message: str = Field(..., min_length=1, max_length=5000, description="User message")
    form_id: Optional[PyObjectId] = Field(None, description="Optional form ID")

    @validator("user_message")
    @classmethod
    def validate_user_message(cls, v):
        """Validate user message."""
        # Remove excessive whitespace
        cleaned = " ".join(v.split())
        if len(cleaned) < 1:
            raise ValueError("Message cannot be empty")
        return cleaned


# Authentication Validation Schemas
class LoginSchema(BaseSchema):
    """Schema for user login."""

    username: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=1, description="User password")


class TokenResponseSchema(BaseSchema):
    """Schema for token responses."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# Query Parameter Schemas
class PaginationSchema(BaseSchema):
    """Schema for pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")


class FormFilterSchema(BaseSchema):
    """Schema for form filtering parameters."""

    status: Optional[str] = None
    context_id: Optional[PyObjectId] = None
    search: Optional[str] = Field(None, max_length=200, description="Search term")

    @validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status filter."""
        if v is not None:
            allowed_statuses = ["draft", "active", "archived"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v


# Error Response Schemas
class ErrorResponseSchema(BaseSchema):
    """Schema for error responses."""

    error: Dict[str, Any] = Field(..., description="Error details")


class ValidationErrorSchema(BaseSchema):
    """Schema for validation error responses."""

    error: Dict[str, Any] = Field(..., description="Validation error details")
    details: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed validation errors")
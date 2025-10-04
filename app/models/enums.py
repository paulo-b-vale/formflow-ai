# app/models/enums.py
from enum import Enum

class UserRole(str, Enum):
    """Enumeration for user roles."""
    USER = "user"
    PROFESSIONAL = "professional"
    ADMIN = "admin"

class ContextType(str, Enum):
    """Enumeration for different work contexts (e.g., hospital, construction)."""
    HOSPITAL = "hospital"
    CONSTRUCTION = "construction"
    MAINTENANCE = "maintenance"
    CONSULTING = "consulting"
    OTHER = "other"

class FormStatus(str, Enum):
    """Enumeration for the status of a form template."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

class ResponseStatus(str, Enum):
    """Enumeration for the status of a user's form response."""
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    
class FormFieldType(str, Enum):
    """Enumeration for the types of fields a form can have."""
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"
    EMAIL = "email"
    PHONE = "phone"
    FILE = "file"
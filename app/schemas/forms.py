# app/schemas/forms.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.enums import ContextType, FormStatus, ResponseStatus
from app.models.forms import FormField
from app.models.file import PyObjectId

# --- Conversation Schemas ---
# ADD THESE TWO CLASSES
class ConversationRequest(BaseModel):
    session_id: str
    user_message: str
    form_id: Optional[str] = None # This makes form_id optional

class ConversationResponse(BaseModel):
    response: str
    session_id: str

# --- Work Context Schemas ---
class WorkContextBase(BaseModel):
    title: str
    description: Optional[str] = None
    context_type: ContextType
    assigned_users: List[str] = []
    assigned_professionals: List[str] = []
    is_active: bool = True

class WorkContextCreate(WorkContextBase):
    pass

class WorkContextUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    context_type: Optional[ContextType] = None
    assigned_users: Optional[List[str]] = None
    assigned_professionals: Optional[List[str]] = None
    is_active: Optional[bool] = None

class WorkContextResponse(WorkContextBase):
    id: PyObjectId = Field(alias="_id")
    created_by: str
    created_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = { datetime: lambda dt: dt.isoformat() }

# --- Form Template Schemas ---
class FormTemplateBase(BaseModel):
    title: str
    description: Optional[str] = None
    context_id: str
    fields: List[FormField] = []
    status: FormStatus = FormStatus.DRAFT

class FormTemplateCreate(FormTemplateBase):
    pass

class FormTemplateUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[List[FormField]] = None
    status: Optional[FormStatus] = None

class FormTemplateResponse(FormTemplateBase):
    id: PyObjectId = Field(alias="_id")
    created_by: str
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = { datetime: lambda dt: dt.isoformat() }

# --- Form Response Schemas ---
class FormResponseBase(BaseModel):
    form_template_id: str
    respondent_name: str
    respondent_phone: Optional[str] = None
    responses: Dict[str, Any] = {}
    missing_fields: List[str] = []

class FormResponseCreate(FormResponseBase):
    pass

class FormResponseUpdate(BaseModel):
    responses: Optional[Dict[str, Any]] = None
    missing_fields: Optional[List[str]] = None
    status: Optional[ResponseStatus] = None
    review_notes: Optional[str] = None # For admin feedback

class FormResponseResponse(FormResponseBase):
    id: PyObjectId = Field(alias="_id")
    context_id: str
    respondent_id: str
    completion_percentage: float
    status: ResponseStatus
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = { datetime: lambda dt: dt.isoformat() }
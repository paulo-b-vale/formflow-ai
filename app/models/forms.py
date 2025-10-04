# app/models/forms.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .enums import ContextType, FormStatus, ResponseStatus, FormFieldType
from .file import MongoBaseModel

class FormField(BaseModel):
    """Defines a single field within a form template."""
    field_id: str = Field(..., description="Unique identifier for the field within the form")
    label: str = Field(..., description="User-friendly label for the field")
    field_type: FormFieldType = Field(..., description="The type of the input field")
    required: bool = Field(default=False)
    description: Optional[str] = Field(None, description="Help text for the user")
    options: Optional[List[str]] = Field(None, description="Options for 'select' or 'multiselect' types")
    placeholder: Optional[str] = Field(None, description="Placeholder text for the input")
    
class WorkContext(MongoBaseModel):
    """Represents a work environment or project, like a specific hospital or construction site."""
    title: str = Field(...)
    description: Optional[str] = Field(None)
    context_type: ContextType = Field(...)
    
    assigned_users: List[str] = Field(default_factory=list)
    assigned_professionals: List[str] = Field(default_factory=list)
    
    created_by: str = Field(...)
    is_active: bool = Field(True)

class FormTemplate(MongoBaseModel):
    """Defines the structure of a form that users can fill out."""
    title: str = Field(...)
    description: Optional[str] = Field(None)
    context_id: str = Field(..., description="The WorkContext this form belongs to")
    
    fields: List[FormField] = Field(default_factory=list)
    
    status: FormStatus = Field(default=FormStatus.DRAFT)
    version: int = Field(1)
    created_by: str = Field(...)

class FormResponse(MongoBaseModel):
    """Stores a user's submission for a specific form."""
    form_template_id: str = Field(...)
    context_id: str = Field(...)
    respondent_id: str = Field(...)
    
    respondent_name: str
    respondent_phone: Optional[str] = Field(None)
    
    responses: Dict[str, Any] = Field(default_factory=dict, description="Stores answers as {field_id: value}")
    missing_fields: List[str] = Field(default_factory=list)
    
    completion_percentage: float = Field(0.0)
    status: ResponseStatus = Field(ResponseStatus.INCOMPLETE)
    
    submitted_at: Optional[datetime] = Field(None)
    reviewed_at: Optional[datetime] = Field(None)
    
    reviewed_by: Optional[str] = Field(None)
    review_notes: Optional[str] = Field(None)
    llm_assistance_used: bool = Field(default=False)

    # --- COMPLETE AUDITING FIELDS ---
    prediction_confidence: Optional[float] = Field(None, description="Confidence score from the initial form prediction")
    prediction_reasoning: Optional[str] = Field(None, description="The LLM's reasoning for choosing this form")
    prediction_context: Optional[List[str]] = Field(None, description="A list of the other form IDs the LLM could have chosen")
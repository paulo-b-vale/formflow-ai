# app/agents/state.py
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

# === GRAPH STATE DEFINITIONS ===

class GraphNodeType(str, Enum):
    """Types of nodes in our agent graph"""
    ROUTER = "router"
    FORM_PREDICTOR = "form_predictor"
    FORM_FILLER = "form_filler"
    QUERY_PROCESSOR = "query_processor"
    REPORT_GENERATOR = "report_generator"
    END = "end"

class AgentState(BaseModel):
    """Central state object that flows through the graph"""
    user_id: str
    user_name: str
    user_input: str
    audio_file_id: Optional[str] = None
    session_id: Optional[str] = None

    # Intent classification
    intent: Optional[str] = None
    confidence: float = 0.0

    # Form-related state
    predicted_form_id: Optional[str] = None
    form_template: Optional[Dict[str, Any]] = None
    form_responses: Dict[str, Any] = {}
    missing_fields: List[str] = []

    # Query-related state
    query_type: Optional[str] = None
    search_filters: Dict[str, Any] = {}
    found_forms: List[Dict[str, Any]] = []

    # Response state
    final_message: str = ""
    requires_response: bool = True
    is_complete: bool = False
    next_node: Optional[str] = None

    # Error handling
    error: Optional[str] = None

class FormState(BaseModel):
    """State for the form filling conversation"""
    session_id: str
    user_id: str
    form_template_id: str = ""
    user_message: Optional[str] = None
    
    # Form filling state
    current_field: Optional[str] = None
    responses: Dict[str, Any] = Field(default_factory=dict)
    completed_fields: List[str] = Field(default_factory=list)
    missing_required_fields: List[str] = Field(default_factory=list) 
    
    # Conversation state
    chat_history: List[Dict[str, str]] = Field(default_factory=list)
    state: str = "STARTING"  # STARTING, FILLING, COMPLETED, ERROR
    is_complete: bool = False
    
    # Response
    final_response: Optional[str] = None
    error_message: Optional[str] = None
    next_node: Optional[str] = None


# === INTENT CLASSIFICATION ===

class IntentType(str, Enum):
    FILL_FORM = "fill_form"
    QUERY_FORMS = "query_forms"
    GENERATE_REPORT = "generate_report"
    CONTINUE_SESSION = "continue_session"
    UNCLEAR = "unclear"

class IntentResult(BaseModel):
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
"""
State Management Module
Centralized state definitions for all agents.

This module defines all state structures used throughout the agent system.
Separating state from logic makes it easier to:
- Track what data flows through the system
- Validate state at runtime
- Serialize/deserialize for persistence
- Version control state schemas
"""

from typing import Dict, Any, List, Optional, TypedDict, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class SessionState(str, Enum):
    """Session lifecycle states"""
    STARTING = "STARTING"
    AWAITING_FORM_CONFIRMATION = "AWAITING_FORM_CONFIRMATION"
    IN_PROGRESS = "IN_PROGRESS"
    CONFIRMATION = "CONFIRMATION"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class AgentType(str, Enum):
    """Types of agents in the system"""
    ROUTER = "router"
    FORM_PREDICTOR = "form_predictor"
    FORM_FILLER = "form_filler"
    FORM_SEARCHER = "form_searcher"
    REPORT_GENERATOR = "report_generator"
    CLARIFICATION = "clarification"
    ERROR = "error"


class ConfidenceLevel(str, Enum):
    """Confidence level categories"""
    HIGH = "high"          # >= 80%
    MEDIUM = "medium"      # 50-80%
    LOW = "low"            # < 50%


# ============================================================================
# TypedDict Definitions (for LangGraph compatibility)
# ============================================================================

class ConversationMessage(TypedDict, total=False):
    """Single message in conversation history"""
    role: Literal["user", "agent", "system"]
    message: str
    timestamp: Optional[str]
    metadata: Optional[Dict[str, Any]]


class AgentState(TypedDict, total=False):
    """
    Core state passed between agents in the graph.

    TypedDict is used for LangGraph compatibility and performance.
    All fields are optional to allow partial state updates.
    """
    # Session identifiers
    session_id: str
    user_id: str
    user_message: str

    # Form context
    form_template_id: Optional[str]
    form_template: Optional[Dict[str, Any]]
    context_id: Optional[str]
    context_info: Optional[Dict[str, Any]]

    # Routing information
    next_node: Optional[str]
    current_agent: Optional[str]

    # Form filling state
    current_field: Optional[str]
    responses: Dict[str, Any]
    completed_fields: List[str]
    missing_required_fields: List[str]

    # Conversation
    conversation_history: List[ConversationMessage]
    chat_history: List[ConversationMessage]  # Alias for compatibility

    # State management
    state: str  # SessionState enum value
    session_state: str  # Alias for compatibility

    # Response
    final_response: Optional[str]
    is_complete: bool

    # Error handling
    error_message: Optional[str]
    requires_clarification: bool
    clarification_message: Optional[str]

    # Confidence tracking
    confidence_score: Optional[float]
    confidence_level: Optional[str]
    confidence_reasoning: Optional[str]

    # Metadata
    timestamp: str
    metadata: Dict[str, Any]

    # File attachments
    file_contents: Optional[List[Dict[str, Any]]]

    # API client (for internal calls)
    api_client: Optional[Any]
    user_token: Optional[str]


# ============================================================================
# Pydantic Models (for validation and serialization)
# ============================================================================

class FieldResponse(BaseModel):
    """Response for a single form field"""
    field_id: str
    value: Any
    confidence: Optional[float] = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    validation_status: Literal["valid", "invalid", "pending"] = "pending"
    validation_message: Optional[str] = None


class ExtractionResult(BaseModel):
    """Result of extracting data from user message"""
    extracted_fields: Dict[str, Any] = {}
    confidence_per_field: Dict[str, float] = {}
    needs_clarification: List[str] = []
    extraction_reasoning: Optional[str] = None


class FormPredictionResult(BaseModel):
    """Result of form prediction"""
    form_template_id: Optional[str] = None
    confidence_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    reasoning: Optional[str] = None
    alternative_forms: List[Dict[str, Any]] = []
    requires_confirmation: bool = False


class AgentResponse(BaseModel):
    """Standard response from any agent"""
    success: bool = True
    message: str
    agent_type: AgentType

    # State updates (optional)
    state_updates: Optional[Dict[str, Any]] = None

    # Next action
    next_node: Optional[str] = None
    is_complete: bool = False

    # Confidence
    confidence: Optional[float] = None

    # Metadata
    processing_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = {}


class FormSubmission(BaseModel):
    """Complete form submission"""
    form_template_id: str
    context_id: Optional[str] = None
    respondent_id: str
    respondent_name: str

    responses: Dict[str, Any]
    completion_percentage: float
    required_completion_percentage: float

    status: Literal["draft", "partial", "complete"] = "draft"

    # Metadata
    session_id: str
    llm_assistance_used: bool = True
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

    metadata: Dict[str, Any] = {}


# ============================================================================
# State Helper Functions
# ============================================================================

def create_initial_state(
    session_id: str,
    user_id: str,
    user_message: str,
    form_template_id: Optional[str] = None,
    **kwargs
) -> AgentState:
    """
    Create initial state for agent graph execution.

    Args:
        session_id: Session identifier
        user_id: User identifier
        user_message: User's message
        form_template_id: Optional form template ID
        **kwargs: Additional state fields

    Returns:
        Complete initial state dict
    """
    return AgentState(
        session_id=session_id,
        user_id=user_id,
        user_message=user_message,
        form_template_id=form_template_id or "",

        # Initialize collections
        responses={},
        completed_fields=[],
        missing_required_fields=[],
        conversation_history=[],
        chat_history=[],

        # Initialize state
        state=SessionState.STARTING.value,
        session_state=SessionState.STARTING.value,

        # Initialize flags
        is_complete=False,
        requires_clarification=False,

        # Initialize optional fields
        next_node=None,
        current_agent=None,
        current_field=None,
        final_response=None,
        error_message=None,
        clarification_message=None,
        confidence_score=None,
        confidence_level=None,
        confidence_reasoning=None,

        # Metadata
        timestamp=datetime.utcnow().isoformat(),
        metadata={},

        # Merge any additional kwargs
        **kwargs
    )


def merge_state_updates(
    current_state: AgentState,
    updates: Dict[str, Any]
) -> AgentState:
    """
    Merge state updates into current state.

    Handles special cases like appending to lists, merging dicts, etc.

    Args:
        current_state: Current state
        updates: Updates to apply

    Returns:
        Updated state
    """
    new_state = current_state.copy()

    for key, value in updates.items():
        if key in ["conversation_history", "chat_history", "completed_fields"]:
            # Append to lists
            if key not in new_state:
                new_state[key] = []
            if isinstance(value, list):
                new_state[key].extend(value)
            else:
                new_state[key].append(value)

        elif key in ["responses", "metadata"]:
            # Merge dicts
            if key not in new_state:
                new_state[key] = {}
            if isinstance(value, dict):
                new_state[key].update(value)
            else:
                new_state[key] = value

        else:
            # Direct assignment
            new_state[key] = value

    return new_state


def validate_state(state: AgentState) -> tuple[bool, Optional[str]]:
    """
    Validate state structure.

    Args:
        state: State to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["session_id", "user_id", "user_message"]

    for field in required_fields:
        if field not in state or not state[field]:
            return False, f"Missing required field: {field}"

    return True, None


def extract_response_from_state(state: AgentState) -> str:
    """
    Extract final response from state.

    Args:
        state: State to extract from

    Returns:
        Response string
    """
    if state.get("final_response"):
        return state["final_response"]

    if state.get("clarification_message"):
        return state["clarification_message"]

    if state.get("error_message"):
        return f"Error: {state['error_message']}"

    return "I'm processing your request..."


def is_state_complete(state: AgentState) -> bool:
    """
    Check if state represents a completed interaction.

    Args:
        state: State to check

    Returns:
        True if complete
    """
    return (
        state.get("is_complete", False) or
        state.get("state") == SessionState.COMPLETED.value or
        state.get("error_message") is not None
    )


def get_state_summary(state: AgentState) -> Dict[str, Any]:
    """
    Get human-readable summary of state.

    Args:
        state: State to summarize

    Returns:
        Summary dict
    """
    return {
        "session_id": state.get("session_id"),
        "state": state.get("state"),
        "current_agent": state.get("current_agent"),
        "form_template_id": state.get("form_template_id"),
        "responses_count": len(state.get("responses", {})),
        "is_complete": state.get("is_complete", False),
        "has_error": state.get("error_message") is not None,
        "confidence": state.get("confidence_score")
    }

"""
Type definitions for agents (temporary compatibility layer).
These types bridge the old architecture with the new core/state.py structure.
"""

from typing import Dict, Any, Optional, TypedDict, List
from enum import Enum

# Type aliases
StateType = Dict[str, Any]
ResponseType = Dict[str, Any]


class NodeType(str, Enum):
    """Types of agent nodes."""
    ROUTER = "router"
    FORM_PREDICTOR = "form_predictor"
    FORM_FILLER = "form_filler"
    FORM_SEARCHER = "form_searcher"
    REPORT_GENERATOR = "report_generator"
    CLARIFICATION = "clarification"
    ERROR = "error"


class NodeResponse(TypedDict, total=False):
    """Standard node response format."""
    final_response: Optional[str]
    next_node: Optional[str]
    is_complete: bool
    confidence_score: Optional[float]
    error_message: Optional[str]
    requires_clarification: bool
    form_template_id: Optional[str]
    reasoning: Optional[str]
    session_state: Optional[str]
    chat_history: Optional[List[Dict[str, Any]]]
    responses_count: int
    search_results: Optional[Dict[str, Any]]
    search_params: Optional[Dict[str, Any]]


# For compatibility with existing code
FormState = StateType


__all__ = [
    "StateType",
    "ResponseType",
    "NodeType",
    "NodeResponse",
    "FormState",
]

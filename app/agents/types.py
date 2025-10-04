"""
Type definitions and common data structures for agents.
"""

from typing import Any, Dict, Optional, Union
from enum import Enum
from dataclasses import dataclass


class NodeType(Enum):
    """Types of agent nodes."""
    ROUTER = "router"
    FORM_PREDICTOR = "form_predictor"
    FORM_FILLER = "form_filler"
    CLARIFICATION = "clarification_handler"
    FORM_SEARCHER = "form_searcher"
    REPORT_GENERATOR = "report_generator"
    ERROR = "error"


@dataclass
class NodeResponse:
    """Standard response format for agent nodes."""
    final_response: Optional[str] = None
    next_node: Optional[str] = None
    is_complete: bool = False
    confidence_score: Optional[float] = None
    error_message: Optional[str] = None
    requires_clarification: bool = False
    form_template_id: Optional[str] = None
    reasoning: Optional[str] = None
    session_state: Optional[str] = None
    chat_history: Optional[list] = None
    responses_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class FormState:
    """Enhanced form state with better type safety."""

    def __init__(self, initial_data: Dict[str, Any] = None):
        self._data = initial_data or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Safely get a value from state."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in state."""
        self._data[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple values."""
        self._data.update(updates)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self._data.copy()

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access."""
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like assignment."""
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator."""
        return key in self._data


# Type aliases for better readability
StateType = Union[Dict[str, Any], FormState]
ResponseType = Union[Dict[str, Any], NodeResponse]
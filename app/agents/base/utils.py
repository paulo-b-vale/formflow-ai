"""
Utility functions for state management and common operations.
"""

from typing import Any, Union
import logging
from ..types import StateType

logger = logging.getLogger(__name__)


def state_get(state: StateType, key: str, default: Any = None) -> Any:
    """
    Safely get a value from LangGraph state with enhanced error handling.
    Handles various state object types including dictionaries, Pydantic models, and custom objects.

    Args:
        state: State object (dict, Pydantic model, or custom object)
        key: Key to retrieve
        default: Default value if key not found

    Returns:
        Value from state or default
    """
    if state is None:
        return default

    # Handle Pydantic models (both v1 and v2)
    if hasattr(state, "model_dump"):  # Pydantic v2
        try:
            state_dict = state.model_dump()
            return state_dict.get(key, default)
        except Exception:
            pass
    elif hasattr(state, "dict"):  # Pydantic v1
        try:
            state_dict = state.dict()
            return state_dict.get(key, default)
        except Exception:
            pass

    # Handle regular dictionaries
    if isinstance(state, dict):
        return state.get(key, default)

    # Handle objects with __getitem__ method (like some LangGraph states)
    if hasattr(state, "__getitem__"):
        try:
            return state[key]
        except (KeyError, TypeError):
            pass

    # Try .get method for dict-like objects
    getter = getattr(state, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except (TypeError, AttributeError):
            pass

    # Try attribute access as fallback
    try:
        return getattr(state, key, default)
    except AttributeError:
        pass

    # Finally return default
    return default


def state_set(state: StateType, key: str, value: Any) -> bool:
    """
    Safely set a value in state object.

    Args:
        state: State object to modify
        key: Key to set
        value: Value to set

    Returns:
        True if successful, False otherwise
    """
    if state is None:
        return False

    try:
        # Handle dictionary-like objects
        if hasattr(state, "__setitem__"):
            state[key] = value
            return True

        # Handle attribute setting
        if hasattr(state, "__setattr__"):
            setattr(state, key, value)
            return True

        return False

    except Exception as e:
        logger.warning(f"Failed to set state key {key}: {e}")
        return False


def validate_state_keys(state: StateType, required_keys: list) -> tuple[bool, list]:
    """
    Validate that required keys exist in state.

    Args:
        state: State object to validate
        required_keys: List of required keys

    Returns:
        Tuple of (is_valid, missing_keys)
    """
    missing_keys = []

    for key in required_keys:
        if state_get(state, key) is None:
            missing_keys.append(key)

    return len(missing_keys) == 0, missing_keys


def merge_states(primary: StateType, secondary: StateType) -> StateType:
    """
    Merge two state objects, with primary taking precedence.

    Args:
        primary: Primary state (takes precedence)
        secondary: Secondary state (used for missing keys)

    Returns:
        Merged state object
    """
    if primary is None:
        return secondary
    if secondary is None:
        return primary

    # If both are dicts, merge them
    if isinstance(primary, dict) and isinstance(secondary, dict):
        merged = secondary.copy()
        merged.update(primary)
        return merged

    # Otherwise, return primary
    return primary
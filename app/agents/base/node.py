"""
Base node class for all agent nodes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from datetime import datetime

from ..types import StateType, ResponseType, NodeResponse, NodeType
from .utils import state_get, state_set
from app.utils.observability import ObservabilityMixin


class BaseNode(ObservabilityMixin, ABC):
    """
    Abstract base class for all agent nodes.
    Provides common functionality and enforces consistent interface.
    """

    def __init__(self, node_type: NodeType, name: Optional[str] = None):
        """
        Initialize base node.

        Args:
            node_type: Type of this node
            name: Optional name for the node
        """
        super().__init__()
        self.node_type = node_type
        self.name = name or node_type.value

    @abstractmethod
    async def execute(self, state: StateType) -> ResponseType:
        """
        Execute the node's main logic.

        Args:
            state: Current state object

        Returns:
            Response object or dictionary
        """
        pass

    async def run(self, state: StateType) -> ResponseType:
        """
        Main entry point for node execution with error handling and logging.

        Args:
            state: Current state object

        Returns:
            Response object or dictionary
        """
        session_id = state_get(state, "session_id", "unknown")
        self.logger.info(f"🔍 BASE_NODE: Starting {self.name} node for session {session_id}")

        try:
            # Debug: Log state structure
            self.logger.info(f"🔍 BASE_NODE: State type: {type(state)}")
            if hasattr(state, '__dict__'):
                state_keys = list(state.__dict__.keys())
                self.logger.info(f"🔍 BASE_NODE: State.__dict__ keys: {state_keys}")
            elif hasattr(state, 'keys'):
                state_keys = list(state.keys())
                self.logger.info(f"🔍 BASE_NODE: State.keys(): {state_keys}")
            else:
                self.logger.info(f"🔍 BASE_NODE: State has no keys method")

            # Try to get specific values
            user_message = state_get(state, "user_message")
            session_id_val = state_get(state, "session_id")
            self.logger.info(f"🔍 BASE_NODE: user_message='{user_message}', session_id='{session_id_val}'")
        except Exception as e:
            self.logger.info(f"🔍 BASE_NODE: Could not analyze state: {e}")

        try:
            # Add execution metadata to state
            state_set(state, "_node_execution_start", datetime.utcnow().isoformat())
            state_set(state, "_current_node", self.name)

            # Execute the node logic
            response = await self.execute(state)

            # Ensure response is in correct format
            if isinstance(response, dict):
                # Convert dict to NodeResponse for consistency
                return self._ensure_response_format(response)
            else:
                return response

        except Exception as e:
            self.logger.exception(f"Error in {self.name} node: {e}")
            return self._create_error_response(str(e))

    def _ensure_response_format(self, response: Dict[str, Any]) -> NodeResponse:
        """
        Ensure response is in NodeResponse format.

        Args:
            response: Response dictionary

        Returns:
            NodeResponse object
        """
        return NodeResponse(
            final_response=response.get("final_response"),
            next_node=response.get("next_node"),
            is_complete=response.get("is_complete", False),
            confidence_score=response.get("confidence_score"),
            error_message=response.get("error_message"),
            requires_clarification=response.get("requires_clarification", False),
            form_template_id=response.get("form_template_id"),
            reasoning=response.get("reasoning"),
            session_state=response.get("session_state"),
            chat_history=response.get("chat_history"),
            responses_count=response.get("responses_count", 0)
        )

    def _create_error_response(self, error_message: str) -> NodeResponse:
        """
        Create standardized error response.

        Args:
            error_message: Error message

        Returns:
            Error response
        """
        return NodeResponse(
            final_response=f"Ocorreu um erro no nó {self.name}. Por favor, tente novamente.",
            next_node="error",
            is_complete=False,
            error_message=error_message
        )

    def _get_required_state_keys(self) -> list:
        """
        Get list of required state keys for this node.
        Override in subclasses to specify required keys.

        Returns:
            List of required state keys
        """
        return ["session_id", "user_message"]

    def _validate_state(self, state: StateType) -> tuple[bool, list]:
        """
        Validate that state has required keys.

        Args:
            state: State to validate

        Returns:
            Tuple of (is_valid, missing_keys)
        """
        required_keys = self._get_required_state_keys()
        missing_keys = []

        for key in required_keys:
            if state_get(state, key) is None:
                missing_keys.append(key)

        return len(missing_keys) == 0, missing_keys

    def _log_state_info(self, state: StateType) -> None:
        """
        Log useful information about current state.

        Args:
            state: Current state
        """
        session_id = state_get(state, "session_id", "unknown")
        user_message = state_get(state, "user_message", "")
        session_state = state_get(state, "session_state", "unknown")

        self.logger.debug(
            f"Node {self.name} - Session: {session_id}, "
            f"State: {session_state}, "
            f"Message length: {len(user_message) if user_message else 0}"
        )
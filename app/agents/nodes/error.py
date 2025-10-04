"""
Error handling node for managing system errors and recovery.
"""

import logging

from ..base import BaseNode, state_get
from ..types import StateType, ResponseType, NodeResponse, NodeType

logger = logging.getLogger(__name__)


class ErrorNode(BaseNode):
    """
    Enhanced error handling node with better messaging and recovery suggestions.
    Provides user-friendly error messages and guides users back to productive workflows.
    """

    def __init__(self):
        """Initialize error node."""
        super().__init__(NodeType.ERROR, "error")

    async def execute(self, state: StateType) -> ResponseType:
        """
        Handle errors with contextual messages and recovery suggestions.

        Args:
            state: Current conversation state

        Returns:
            Error response with recovery guidance
        """
        error_message = state_get(state, "error_message")
        session_id = state_get(state, "session_id")

        self.logger.error(f"📍 ERROR_NODE: ENTRY - state type: {type(state)}")
        if hasattr(state, 'keys'):
            self.logger.error(f"📍 ERROR_NODE: Available state keys: {list(state.keys())}")
        elif hasattr(state, '__dict__'):
            self.logger.error(f"📍 ERROR_NODE: Available state attributes: {list(state.__dict__.keys())}")

        # Check FormState _data contents
        if hasattr(state, '_data'):
            self.logger.error(f"📍 ERROR_NODE: FormState._data contents: {state._data}")
            self.logger.error(f"📍 ERROR_NODE: FormState._data keys: {list(state._data.keys()) if state._data else 'None'}")

        self.logger.error(f"📍 ERROR_NODE: session_id='{session_id}', error_message='{error_message}'")

        if not error_message:
            error_message = "Ocorreu um erro inesperado. Por favor, tente reformular sua solicitação."

        # Provide helpful error message based on context
        contextual_message = self._generate_error_message(error_message)

        return NodeResponse(
            final_response=contextual_message,
            is_complete=False,
            error_message=error_message,
            next_node=None
        )

    def _generate_error_message(self, original_error: str) -> str:
        """
        Generate contextual error message with recovery suggestions.

        Args:
            original_error: Original error message

        Returns:
            User-friendly error message in Portuguese
        """
        return f"""Encontrei um problema: {original_error}

Deixe-me ajudá-lo a voltar ao caminho certo. Você pode:
• Tentar reformular sua solicitação
• Pedir-me para ajudá-lo a preencher um formulário específico
• Buscar formulários enviados existentes
• Perguntar sobre o que posso fazer

O que você gostaria de tentar?"""

    def _get_required_state_keys(self) -> list:
        """Get required state keys for error handling."""
        return []  # No required keys for error handling
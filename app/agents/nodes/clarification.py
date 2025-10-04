"""
Clarification node for handling unclear user requests.
"""

import logging

from ..base import BaseNode, state_get
from ..types import StateType, ResponseType, NodeResponse, NodeType
from app.utils.confidence_system import ConfidenceManager

logger = logging.getLogger(__name__)


class ClarificationNode(BaseNode):
    """
    Enhanced clarification handler with better response generation.
    Handles cases where user intent is unclear or requires additional information.
    """

    def __init__(self):
        """Initialize clarification node."""
        super().__init__(NodeType.CLARIFICATION, "clarification_handler")
        self.confidence_manager = ConfidenceManager()

    async def execute(self, state: StateType) -> ResponseType:
        """
        Generate clarification response with context awareness.

        Args:
            state: Current conversation state

        Returns:
            Clarification response
        """
        user_message = state_get(state, "user_message", "")

        self.logger.info(f"Generating clarification for message: '{user_message[:50]}...'")

        # Generate contextual clarification message
        clarification_message = self._generate_clarification_message(user_message)

        return NodeResponse(
            final_response=clarification_message,
            is_complete=False,
            requires_clarification=True,
            confidence_score=0.3
        )

    def _generate_clarification_message(self, user_message: str) -> str:
        """
        Generate contextual clarification message.

        Args:
            user_message: Original user message

        Returns:
            Clarification message in Portuguese
        """
        return f"""Quero ajudá-lo, mas preciso de mais clareza sobre sua solicitação: "{user_message}"

Posso ajudá-lo com:

Preencher um formulário - Posso ajudá-lo a encontrar o formulário certo e guiá-lo no preenchimento
Buscar formulários existentes - Posso ajudá-lo a encontrar formulários ou respostas enviados anteriormente
Gerar relatórios - Posso criar resumos e análises de dados de formulários

Você pode me dizer qual destes você gostaria de fazer, ou fornecer mais detalhes específicos sobre o que você precisa?"""

    def _get_required_state_keys(self) -> list:
        """Get required state keys for clarification."""
        return []  # No required keys for clarification
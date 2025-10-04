"""
Form filler node for handling form completion interactions.
"""

import logging
from typing import Dict, Any

from ..base import BaseNode, state_get
from ..types import StateType, ResponseType, NodeResponse, NodeType
from app.agents.enhanced_form_filler_agent import EnhancedFormFillerAgent
from app.sessions.session_manager import SessionManager, SessionState
from app.database import db

logger = logging.getLogger(__name__)


class FormFillerNode(BaseNode):
    """
    Enhanced form filler node with comprehensive error handling and multi-field extraction.
    Handles the complete form filling workflow including field validation and submission.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize form filler node.

        Args:
            session_manager: Session manager for state persistence
        """
        super().__init__(NodeType.FORM_FILLER, "form_filler")
        self.session_manager = session_manager

    async def execute(self, state: StateType) -> ResponseType:
        """
        Execute form filling logic with comprehensive error handling.

        Args:
            state: Current conversation state

        Returns:
            Form filling response
        """
        session_id = state_get(state, "session_id")
        user_message = state_get(state, "user_message")
        predicted_form_id = state_get(state, "form_template_id")

        self.logger.info(f"Processing form filling for session: {session_id}, form: {predicted_form_id}")

        # Handle prediction confidence and clarification
        confidence_score = state_get(state, "confidence_score", 1.0)
        requires_clarification = state_get(state, "requires_clarification", False)
        clarification_message = state_get(state, "clarification_message")

        # Return clarification if needed
        if requires_clarification and clarification_message:
            self.logger.info(f"Returning clarification for session {session_id}")
            return NodeResponse(
                final_response=clarification_message,
                is_complete=False,
                confidence_score=confidence_score,
                requires_clarification=True
            )

        # Get session data
        session_data = await self.session_manager.get_session(session_id)
        if not session_data:
            self.logger.error(f"Session {session_id} not found in form filler")
            return self._create_session_not_found_response()

        # Set predicted form ID if available
        if predicted_form_id and not getattr(session_data, "form_template_id", None):
            session_data.form_template_id = predicted_form_id
            self.logger.info(f"Set form template ID: {predicted_form_id} for session {session_id}")

            # Log prediction metadata
            reasoning = state_get(state, "reasoning")
            form_details = state_get(state, "form_details", {})

            if reasoning:
                self.logger.info(f"Form prediction reasoning: {reasoning}")
            if form_details:
                form_title = form_details.get('title', 'Unknown Form')
                self.logger.info(f"Starting form: {form_title}")

        # Validate form template ID
        if not getattr(session_data, "form_template_id", None):
            error_message = state_get(state, "error_message",
                                      "Não tenho certeza de qual formulário você gostaria de preencher. Você poderia ser mais específico?")
            self.logger.warning(f"No form template ID for session {session_id}")
            return NodeResponse(
                final_response=error_message,
                is_complete=False,
                error_message="No form template ID"
            )

        # Create and run form filler agent
        try:
            agent = EnhancedFormFillerAgent(db, session_data)

            # Process the interaction based on session state
            self.logger.info(f"🔍 FORM_FILLER_NODE: session_state={session_data.state}, user_message='{user_message}'")

            if getattr(session_data, "state", None) == SessionState.STARTING or session_data.state == "STARTING":
                self.logger.info(f"Starting new form conversation for session {session_id}")
                response = await agent.start_conversation()
            else:
                self.logger.info(f"🔀 CALLING agent.process_message for session {session_id} with state {session_data.state}")
                response = await agent.process_message(user_message)

            # Save updated session
            await self.session_manager.save_session(agent.session_data)

            # Build comprehensive response
            return self._build_agent_response(response, confidence_score, agent.session_data)

        except Exception as e:
            self.logger.exception(f"Error creating or running form filler agent: {e}")
            return self._create_agent_error_response(str(e))

    def _create_session_not_found_response(self) -> NodeResponse:
        """Create response for missing session."""
        return NodeResponse(
            final_response="Não consegui encontrar sua sessão. Vamos começar do zero - com que tipo de formulário você precisa de ajuda?",
            is_complete=False,
            error_message="Session not found"
        )

    def _create_agent_error_response(self, error_message: str) -> NodeResponse:
        """Create response for agent errors."""
        return NodeResponse(
            final_response=f"Encontrei um problema ao processar o formulário: {error_message}. Por favor, tente novamente.",
            is_complete=False,
            error_message=error_message
        )

    def _build_agent_response(self, response: Dict[str, Any], confidence_score: float, session_data) -> NodeResponse:
        """
        Build comprehensive response from agent result.

        Args:
            response: Agent response dictionary
            confidence_score: Prediction confidence score
            session_data: Updated session data

        Returns:
            Structured node response
        """
        final_response = response.get("message", "")

        # Ensure we have a response message
        if not final_response:
            self.logger.warning(f"Empty response from agent")
            final_response = "Estou processando sua solicitação. Você poderia fornecer mais detalhes?"

        return NodeResponse(
            final_response=final_response,
            is_complete=response.get("is_complete", False),
            confidence_score=confidence_score,
            chat_history=getattr(session_data, 'conversation_history', []),
            responses_count=len(getattr(session_data, 'responses', {})),
            session_state=getattr(session_data, 'state', {}).value if hasattr(getattr(session_data, 'state', {}), 'value') else str(getattr(session_data, 'state', 'unknown'))
        )

    def _get_required_state_keys(self) -> list:
        """Get required state keys for form filling."""
        return ["session_id", "user_message"]
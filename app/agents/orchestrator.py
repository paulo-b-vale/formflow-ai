"""
Conversation graph orchestrator for managing agent workflow.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from .types import FormState, NodeResponse
from .base import state_get
from .nodes import RouterNode, ClarificationNode, FormFillerNode, ErrorNode
from .enhanced_form_predictor_node import EnhancedFormPredictorNode
from .form_searcher_node import FormSearcherNode
from .report_generator_node import ReportGeneratorNode
from app.sessions.session_manager import SessionManager
from app.utils.observability import ObservabilityMixin, monitor
from app.utils.confidence_system import ConfidenceManager

logger = logging.getLogger(__name__)


class ConversationGraphOrchestrator(ObservabilityMixin):
    """
    Enhanced orchestrator with better state management and error handling.
    Manages the conversation flow between different agent nodes.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize orchestrator with session manager.

        Args:
            session_manager: Session manager for state persistence
        """
        super().__init__()
        self.session_manager = session_manager
        self.confidence_manager = ConfidenceManager()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Build the conversation graph with enhanced error handling.

        Returns:
            Compiled StateGraph ready for execution
        """
        workflow = StateGraph(dict)

        # Initialize nodes with dependency injection
        router_node = RouterNode(self.session_manager)
        form_predictor_node = EnhancedFormPredictorNode()
        form_filler_node = FormFillerNode(self.session_manager)
        clarification_handler = ClarificationNode()
        form_searcher = FormSearcherNode()
        report_generator = ReportGeneratorNode()
        error_node = ErrorNode()

        # Add nodes to workflow
        workflow.add_node("router", self._wrap_node(router_node))
        workflow.add_node("form_predictor", self._wrap_node(form_predictor_node))
        workflow.add_node("form_filler", self._wrap_node(form_filler_node))
        workflow.add_node("clarification_handler", self._wrap_node(clarification_handler))
        workflow.add_node("form_searcher", self._wrap_node(form_searcher))
        workflow.add_node("report_generator", self._wrap_node(report_generator))
        workflow.add_node("error", self._wrap_node(error_node))

        # Set entry point
        workflow.set_entry_point("router")

        # Enhanced router conditional edges with error handling
        workflow.add_conditional_edges(
            "router",
            self._router_decision,
            {
                "form_predictor": "form_predictor",
                "form_filler": "form_filler",
                "clarification_handler": "clarification_handler",
                "form_searcher": "form_searcher",
                "report_generator": "report_generator",
                "error": "error",
            },
        )

        # Enhanced form predictor conditional edges
        workflow.add_conditional_edges(
            "form_predictor",
            self._form_predictor_router,
            {
                "form_filler": "form_filler",
                "error": "error",
            },
        )

        # All terminal nodes end the workflow
        workflow.add_edge("form_filler", END)
        workflow.add_edge("clarification_handler", END)
        workflow.add_edge("form_searcher", END)
        workflow.add_edge("report_generator", END)
        workflow.add_edge("error", END)

        return workflow.compile()

    def _wrap_node(self, node_instance):
        """
        Wrap node instance to handle different response formats.

        Args:
            node_instance: Node instance to wrap

        Returns:
            Wrapped node function
        """
        async def wrapped_node(state):
            try:
                # Log session info for debugging
                node_name = getattr(node_instance, 'name', node_instance.__class__.__name__)
                session_id = state_get(state, "session_id") if hasattr(state, 'get') or hasattr(state, '__getitem__') else None
                logger.info(f"🔍 WRAPPED_NODE: {node_name} executing with session_id='{session_id}'")

                # Call the node's run method
                response = await node_instance.run(state)

                # Convert NodeResponse to dict and merge with original state for LangGraph compatibility
                if isinstance(response, NodeResponse):
                    # Merge original state with response to preserve session_id and other fields
                    response_dict = response.to_dict()
                    if hasattr(state, 'get') or hasattr(state, '__getitem__'):
                        # Preserve essential fields from original state
                        merged_response = {
                            "session_id": state_get(state, "session_id"),
                            "user_id": state_get(state, "user_id"),
                            "user_message": state_get(state, "user_message"),
                            "form_template_id": state_get(state, "form_template_id"),
                        }
                        # Add response fields (these override if present)
                        merged_response.update(response_dict)
                        return merged_response
                    else:
                        return response_dict
                else:
                    return response

            except Exception as e:
                node_name = getattr(node_instance, 'name', node_instance.__class__.__name__)
                logger.exception(f"Error in wrapped node {node_name}: {e}")
                # Preserve ALL essential state when error occurs
                session_id = state_get(state, "session_id") if hasattr(state, 'get') or hasattr(state, '__getitem__') else None
                logger.error(f"🚨 WRAPPED_NODE: {node_name} failed with session_id='{session_id}', error: {e}")
                return {
                    "session_id": state_get(state, "session_id"),
                    "user_id": state_get(state, "user_id"),
                    "user_message": state_get(state, "user_message"),
                    "form_template_id": state_get(state, "form_template_id"),
                    "final_response": f"Erro no nó {node_instance.name}: {str(e)}",
                    "next_node": "error",
                    "error_message": str(e)
                }

        return wrapped_node

    def _router_decision(self, state) -> str:
        """
        Router decision function with error handling.

        Args:
            state: Current state

        Returns:
            Next node name
        """
        try:
            next_node = state_get(state, "next_node", "error")
            logger.debug(f"Router decision: {next_node}")
            return next_node
        except Exception as e:
            logger.error(f"Error in router decision: {e}")
            return "error"

    def _form_predictor_router(self, state) -> str:
        """
        Form predictor routing logic.

        Args:
            state: Current state

        Returns:
            Next node name
        """
        try:
            form_template_id = state_get(state, "form_template_id")
            error_message = state_get(state, "error_message")
            requires_clarification = state_get(state, "requires_clarification", False)

            logger.debug(
                f"Form predictor router - form_id: {form_template_id}, "
                f"error: {error_message}, clarification: {requires_clarification}"
            )

            if error_message:
                return "error"
            elif requires_clarification:
                return "form_filler"  # Form filler can handle clarification
            elif form_template_id is not None and str(form_template_id).strip() != "":
                return "form_filler"
            else:
                return "error"

        except Exception as e:
            logger.error(f"Error in form predictor router: {e}")
            return "error"

    @monitor
    async def invoke(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced graph invocation with comprehensive error handling.

        Args:
            initial_state: Initial state dictionary

        Returns:
            Final state after graph execution
        """
        session_id = initial_state.get("session_id", "unknown")

        try:
            logger.info(f"📍 ORCHESTRATOR: ENTRY - Starting graph execution for session {session_id}")
            logger.info(f"📍 ORCHESTRATOR: Initial state keys: {list(initial_state.keys())}")
            logger.info(f"📍 ORCHESTRATOR: user_message='{initial_state.get('user_message')}', session_id='{initial_state.get('session_id')}'")

            # Ensure required state fields are present with proper defaults
            enhanced_state = {
                "initial_confidence_score": 1.0,
                "confidence_level": "high",
                "timestamp": datetime.utcnow().isoformat(),
                "current_field": None,
                "responses": {},
                "completed_fields": [],
                "missing_required_fields": [],
                "chat_history": [],
                "state": "STARTING",
                "is_complete": False,
                "final_response": None,
                "error_message": None,
                "next_node": None,
                **initial_state
            }

            # Debug: Log enhanced state before graph execution
            logger.info(f"🔍 ORCHESTRATOR: Enhanced state keys: {list(enhanced_state.keys())}")
            logger.info(f"🔍 ORCHESTRATOR: About to execute graph with user_message='{enhanced_state.get('user_message')}', session_id='{enhanced_state.get('session_id')}'")

            # Execute the graph
            logger.info(f"📍 ORCHESTRATOR: About to call graph.ainvoke() with session_id='{enhanced_state.get('session_id')}'")
            final_state = await self.graph.ainvoke(enhanced_state)
            logger.info(f"📍 ORCHESTRATOR: Graph.ainvoke() returned, final_state session_id='{final_state.get('session_id') if final_state else None}'")

            if not final_state:
                logger.error(f"Graph returned None state for session {session_id}")
                return self._create_error_state(session_id, "Graph execution returned None")

            # Validate final state has required fields
            if not state_get(final_state, "final_response"):
                logger.warning(f"No final_response in final state for session {session_id}")
                # Try to extract from other possible fields
                response = (
                    state_get(final_state, "message") or
                    state_get(final_state, "response") or
                    state_get(final_state, "content") or
                    "Estou processando sua solicitação. Por favor, forneça mais detalhes se necessário."
                )
                final_state["final_response"] = response

            logger.info(f"Graph execution completed successfully for session {session_id}")
            return final_state

        except Exception as e:
            logger.exception(f"Graph execution failed for session {session_id}: {e}")
            return self._create_error_state(session_id, str(e))

    def _create_error_state(self, session_id: str, error_message: str) -> Dict[str, Any]:
        """
        Create error state for graph failures.

        Args:
            session_id: Session identifier
            error_message: Error description

        Returns:
            Error state dictionary
        """
        return {
            "final_response": "Encontrei um erro inesperado ao processar sua solicitação. Por favor, tente novamente e entre em contato com o suporte se o problema persistir.",
            "is_complete": False,
            "error_message": error_message,
            "session_id": session_id
        }
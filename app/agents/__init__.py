# app/agents/__init___fixed.py
from langgraph.graph import StateGraph, END
from app.agents.state import FormState
from app.agents.enhanced_form_filler_agent import EnhancedFormFillerAgent
from app.agents.enhanced_form_predictor_node import EnhancedFormPredictorNode
from app.sessions.session_manager import SessionManager, SessionData, SessionState
from app.utils.observability import ObservabilityMixin, monitor
from app.database import db
from app.utils.langchain_utils import get_gemini_llm
from app.utils.confidence_system import ConfidenceManager
import httpx
import logging
from datetime import datetime
from app.config.settings import settings
from app.agents.form_searcher_node import FormSearcherNode
from app.agents.report_generator_node import ReportGeneratorNode

logger = logging.getLogger(__name__)

def _state_get(state, key, default=None):
    """
    Safely get a value from LangGraph state with enhanced error handling.
    Handles various state object types including dictionaries, Pydantic models, and custom objects.
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


class EnhancedRouterNode(ObservabilityMixin):
    """Enhanced routing with better error handling and logging."""
    
    def __init__(self, session_manager: SessionManager = None):
        self.llm = get_gemini_llm()
        self.session_manager = session_manager

    async def run(self, state: FormState):
        """Enhanced routing with optimized first message handling."""
        try:
            user_message = _state_get(state, "user_message")
            session_id = _state_get(state, "session_id")
            session_state = _state_get(state, "session_state", "STARTING")

            logger.info(f"Router processing message: '{user_message}' for session: {session_id}, state: {session_state}")

            if not user_message:
                logger.info("No user message found, routing to form predictor")
                return {"next_node": "form_predictor"}

            # Check for existing form session
            session_data = await self._get_session_data(session_id)
            if session_data and hasattr(session_data, 'form_template_id') and session_data.form_template_id:
                # Check if session is completed
                session_state = getattr(session_data, 'state', None)
                if hasattr(session_state, 'value'):
                    state_value = session_state.value
                else:
                    state_value = str(session_state) if session_state else None

                if state_value == "COMPLETED":
                    logger.info(f"Session {session_id} is completed, routing to form predictor for new request")
                    return {"next_node": "form_predictor"}
                else:
                    logger.info(f"Continuing existing form session with template: {session_data.form_template_id}, state: {state_value}")
                    return {"next_node": "form_filler"}

            # Optimization: Skip intent classification for first messages
            # Most first messages are form requests, so default to form_predictor
            if session_state == "STARTING" or not session_data:
                logger.info("First message detected, skipping intent classification - routing to form predictor")
                return {"next_node": "form_predictor"}

            # Enhanced intent classification only for subsequent messages
            intent = await self._classify_intent(user_message)
            logger.info(f"Classified intent: '{intent}' for message: '{user_message}'")

            intent_mapping = {
                "fill_form": "form_predictor",
                "search_forms": "form_searcher",
                "generate_report": "report_generator",
                "clarification_needed": "clarification_handler"
            }

            next_node = intent_mapping.get(intent, "form_predictor")
            logger.info(f"Routing to node: {next_node}")

            return {"next_node": next_node}

        except Exception as e:
            logger.exception(f"Error in router node: {e}")
            return {"next_node": "error", "error_message": f"Router error: {str(e)}"}

    async def _classify_intent(self, user_message: str) -> str:
        """Enhanced intent classification with better prompting."""
        prompt = f"""You are an expert at classifying user intents for a form management system.

Based on the user's message, classify the intent into one of the following categories:

1. **fill_form** - User wants to start, continue, or interact with filling out a form
   Examples: "I need to fill out a form", "help me with the safety report", "I want to submit information"

2. **search_forms** - User wants to find, query, or search through existing form submissions  
   Examples: "show me yesterday's reports", "find John's safety forms", "what forms were submitted today"

3. **generate_report** - User wants analytics, summaries, or reports from form data
   Examples: "generate a summary", "show me analytics", "create a report", "what are the trends"

4. **clarification_needed** - User's request is unclear or could match multiple intents
   Examples: vague requests, ambiguous language

User message: "{user_message}"

Respond with ONLY the category name (fill_form, search_forms, generate_report, or clarification_needed).
"""

        try:
            response = await self.llm.ainvoke(prompt)
            intent = response.content.lower().strip()

            # Normalize intent response
            if "fill_form" in intent or "form" in intent:
                return "fill_form"
            elif "search" in intent:
                return "search_forms"
            elif "report" in intent or "generate" in intent:
                return "generate_report"
            else:
                return "clarification_needed"
                
        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return "fill_form"  # Safe default

    async def _get_session_data(self, session_id):
        """Get session data with enhanced error handling."""
        if self.session_manager and session_id:
            try:
                return await self.session_manager.get_session(session_id)
            except Exception as e:
                logger.error(f"Error retrieving session data: {e}")
                return None
        return None


class ClarificationHandlerNode(ObservabilityMixin):
    """Enhanced clarification handler with better response generation."""
    
    def __init__(self):
        self.confidence_manager = ConfidenceManager()
    
    async def run(self, state: FormState):
        """Generate clarification response with context awareness."""
        try:
            user_message = _state_get(state, "user_message", "")
            
            # Generate contextual clarification message
            clarification_message = f"""Quero ajudá-lo, mas preciso de mais clareza sobre sua solicitação: "{user_message}"

Posso ajudá-lo com:

Preencher um formulário - Posso ajudá-lo a encontrar o formulário certo e guiá-lo no preenchimento
Buscar formulários existentes - Posso ajudá-lo a encontrar formulários ou respostas enviados anteriormente
Gerar relatórios - Posso criar resumos e análises de dados de formulários

Você pode me dizer qual destes você gostaria de fazer, ou fornecer mais detalhes específicos sobre o que você precisa?"""

            return {
                "final_response": clarification_message,
                "is_complete": False,
                "requires_clarification": True,
                "confidence_score": 0.3
            }
            
        except Exception as e:
            logger.exception(f"Error in clarification handler: {e}")
            return {
                "final_response": "Preciso de mais informações para ajudá-lo. Você poderia esclarecer o que está procurando?",
                "is_complete": False,
                "error_message": str(e)
            }


class EnhancedFormFillerNode(ObservabilityMixin):
    """Enhanced form filler with better response handling."""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    async def run(self, state: FormState):
        """Enhanced form filling with comprehensive error handling."""
        try:
            session_id = _state_get(state, "session_id")
            user_message = _state_get(state, "user_message")
            predicted_form_id = _state_get(state, "form_template_id")
            
            logger.info(f"Form filler processing session: {session_id}, form: {predicted_form_id}")
            
            # Handle prediction confidence and clarification
            confidence_score = _state_get(state, "confidence_score", 1.0)
            requires_clarification = _state_get(state, "requires_clarification", False)
            clarification_message = _state_get(state, "clarification_message")
            
            # Return clarification if needed
            if requires_clarification and clarification_message:
                logger.info(f"Returning clarification for session {session_id}")
                return {
                    "final_response": clarification_message,
                    "is_complete": False,
                    "confidence_score": confidence_score,
                    "requires_clarification": True
                }

            # Get session data
            session_data = await self.session_manager.get_session(session_id)
            if not session_data:
                logger.error(f"Session {session_id} not found in form filler")
                return {
                    "final_response": "I couldn't find your session. Let's start fresh - what kind of form do you need help with?",
                    "is_complete": False,
                    "error_message": "Session not found"
                }

            # Set predicted form ID if available
            if predicted_form_id and not getattr(session_data, "form_template_id", None):
                session_data.form_template_id = predicted_form_id
                logger.info(f"Set form template ID: {predicted_form_id} for session {session_id}")
                
                # Log prediction metadata
                reasoning = _state_get(state, "reasoning")
                form_details = _state_get(state, "form_details", {})
                
                if reasoning:
                    logger.info(f"Form prediction reasoning: {reasoning}")
                if form_details:
                    form_title = form_details.get('title', 'Unknown Form')
                    logger.info(f"Starting form: {form_title}")

            # Validate form template ID
            if not getattr(session_data, "form_template_id", None):
                error_message = _state_get(state, "error_message", 
                    "I'm not sure which form you'd like to fill out. Could you please be more specific?")
                logger.warning(f"No form template ID for session {session_id}")
                return {
                    "final_response": error_message,
                    "is_complete": False,
                    "error_message": "No form template ID"
                }

            # Create and run form filler agent
            agent = EnhancedFormFillerAgent(db, session_data)

            # Process the interaction based on session state
            if getattr(session_data, "state", None) == SessionState.STARTING or session_data.state == "STARTING":
                logger.info(f"Starting new form conversation for session {session_id}")

                # ENHANCED: Check if user provided data in their first message
                user_message_content = _state_get(state, "user_message", "").strip()
                if user_message_content and len(user_message_content) > 10:  # More than just a greeting
                    logger.info(f"User provided data in first message, processing with extraction: {user_message_content}")
                    # Start conversation then immediately process the user's message
                    response = await agent.start_conversation()

                    # If start_conversation succeeded, process the user's message for field extraction
                    if response.get("is_complete") is False:  # Form started successfully
                        extraction_response = await agent.process_message(user_message_content)
                        # Merge the responses - show welcome + extraction results
                        welcome_msg = response.get("message", "")
                        extraction_msg = extraction_response.get("message", "")

                        if extraction_msg and "Informações capturadas" in extraction_msg:
                            # User provided useful data, combine messages
                            combined_msg = f"{welcome_msg}\n\n{extraction_msg}"
                            response["message"] = combined_msg
                        else:
                            # No useful data extracted, just show the welcome + current question
                            response = extraction_response
                else:
                    # Standard start conversation
                    response = await agent.start_conversation()
            else:
                logger.info(f"Processing message for ongoing session {session_id}")
                response = await agent.process_message(user_message)

            # Save updated session
            await self.session_manager.save_session(agent.session_data)

            # Build comprehensive response
            final_response = {
                "final_response": response.get("message", ""),
                "is_complete": response.get("is_complete", False),
                "confidence_score": confidence_score,
                "chat_history": agent.session_data.conversation_history,
                "responses_count": len(agent.session_data.responses),
                "session_state": agent.session_data.state.value if isinstance(agent.session_data.state, SessionState) else agent.session_data.state
            }
            
            # Ensure we have a response message
            if not final_response["final_response"]:
                logger.warning(f"Empty response from agent for session {session_id}")
                final_response["final_response"] = "I'm processing your request. Could you provide more details?"
            
            logger.info(f"Form filler completed for session {session_id}, complete: {final_response['is_complete']}")
            return final_response
            
        except Exception as e:
            logger.exception(f"Error in form filler node: {e}")
            return {
                "final_response": f"I encountered an issue while processing the form: {str(e)}. Please try again.",
                "is_complete": False,
                "error_message": str(e)
            }


class ErrorNode(ObservabilityMixin):
    """Enhanced error handling node with better messaging."""
    
    async def run(self, state: FormState):
        """Handle errors with contextual messages."""
        try:
            error_message = _state_get(state, "error_message")
            session_id = _state_get(state, "session_id")
            
            logger.error(f"Error node activated for session {session_id}: {error_message}")
            
            if not error_message:
                error_message = "An unexpected error occurred. Please try rephrasing your request."
            
            # Provide helpful error message based on context
            contextual_message = f"""I encountered an issue: {error_message}

Let me help you get back on track. You can:
• Try rephrasing your request
• Ask me to help you fill out a specific form
• Search for existing form submissions
• Ask for help with what I can do

What would you like to try?"""
            
            return {
                "final_response": contextual_message,
                "is_complete": False,
                "error": True,
                "recoverable": True
            }
            
        except Exception as e:
            logger.exception(f"Error in error node: {e}")
            return {
                "final_response": "I'm experiencing technical difficulties. Please try again later.",
                "is_complete": True,
                "error": True,
                "recoverable": False
            }


class ConversationGraphOrchestrator(ObservabilityMixin):
    """Enhanced orchestrator with better state management and error handling."""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.confidence_manager = ConfidenceManager()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the conversation graph with enhanced error handling."""
        workflow = StateGraph(FormState)

        # Initialize nodes with error handling
        router_node = EnhancedRouterNode(self.session_manager)
        form_predictor_node = EnhancedFormPredictorNode()
        form_filler_node = EnhancedFormFillerNode(self.session_manager)
        clarification_handler = ClarificationHandlerNode()
        form_searcher = FormSearcherNode()
        report_generator = ReportGeneratorNode()
        error_node = ErrorNode()

        # Add nodes to workflow
        workflow.add_node("router", router_node.run)
        workflow.add_node("form_predictor", form_predictor_node.run)
        workflow.add_node("form_filler", form_filler_node.run)
        workflow.add_node("clarification_handler", clarification_handler.run)
        workflow.add_node("form_searcher", form_searcher.run)
        workflow.add_node("report_generator", report_generator.run)
        workflow.add_node("error", error_node.run)

        # Set entry point
        workflow.set_entry_point("router")

        # Enhanced router conditional edges with error handling
        def router_decision(state):
            try:
                next_node = _state_get(state, "next_node", "error")
                logger.debug(f"Router decision: {next_node}")
                return next_node
            except Exception as e:
                logger.error(f"Error in router decision: {e}")
                return "error"

        workflow.add_conditional_edges(
            "router",
            router_decision,
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
        def form_predictor_router(state):
            try:
                form_template_id = _state_get(state, "form_template_id")
                error_message = _state_get(state, "error_message")
                requires_clarification = _state_get(state, "requires_clarification", False)
                
                logger.debug(f"Form predictor router - form_id: {form_template_id}, error: {error_message}, clarification: {requires_clarification}")
                
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

        workflow.add_conditional_edges(
            "form_predictor",
            form_predictor_router,
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

    @monitor
    async def invoke(self, initial_state: dict):
        """Enhanced graph invocation with comprehensive error handling."""
        session_id = initial_state.get("session_id", "unknown")
        
        try:
            logger.info(f"Starting graph execution for session {session_id}")
            logger.debug(f"Initial state keys: {list(initial_state.keys())}")
            
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
            
            # Execute the graph
            final_state = await self.graph.ainvoke(enhanced_state)
            
            if not final_state:
                logger.error(f"Graph returned None state for session {session_id}")
                return {
                    "final_response": "I encountered an issue processing your request. Please try again.",
                    "is_complete": False,
                    "error_message": "Graph execution returned None"
                }
            
            # Validate final state has required fields
            if not _state_get(final_state, "final_response"):
                logger.warning(f"No final_response in final state for session {session_id}")
                # Try to extract from other possible fields
                response = (
                    _state_get(final_state, "message") or 
                    _state_get(final_state, "response") or 
                    _state_get(final_state, "content") or
                    "I'm processing your request. Please provide more details if needed."
                )
                final_state["final_response"] = response
            
            logger.info(f"Graph execution completed successfully for session {session_id}")
            return final_state
            
        except Exception as e:
            logger.exception(f"Graph execution failed for session {session_id}: {e}")
            return {
                "final_response": "I encountered an unexpected error while processing your request. Please try again, and contact support if the problem persists.",
                "is_complete": False,
                "error_message": str(e),
                "session_id": session_id
            }
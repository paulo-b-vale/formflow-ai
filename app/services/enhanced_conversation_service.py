# app/services/enhanced_conversation_service_fixed.py
from typing import Dict, Any, List
import asyncio
import json
import logging
from datetime import datetime
from bson import ObjectId
import httpx
from urllib.parse import urljoin

from app.services.base_service import BaseService
from app.agents.orchestrator import ConversationGraphOrchestrator
from app.sessions.session_manager import SessionManager, SessionData, RedisManager, InMemorySessionStorage, SessionState
from app.database import get_redis, db
from app.config.settings import settings
from app.models.conversation_log import ConversationLog

logger = logging.getLogger(__name__)


def _normalize_state(state: Any) -> Dict[str, Any]:
    """Convert a state object into a plain dictionary suitable for storage."""
    if state is None:
        return {}
    
    # Handle Pydantic v2
    if hasattr(state, "model_dump") and callable(state.model_dump):
        try:
            return state.model_dump()
        except Exception:
            pass
    
    # Handle Pydantic v1
    if hasattr(state, "dict") and callable(state.dict):
        try:
            return state.dict()
        except Exception:
            pass
    
    # Handle regular dict
    if isinstance(state, dict):
        return dict(state)
    
    # Handle objects with __dict__
    try:
        return dict(vars(state))
    except Exception:
        return {"repr": repr(state)}


class EnhancedConversationService(BaseService):
    """Enhanced conversation service with improved session handling and response extraction."""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EnhancedConversationService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    async def initialize(self):
        """Initialize the service with enhanced error handling."""
        await super().initialize()
        
        try:
            # Initialize Redis with fallback
            self.redis_manager = RedisManager()
            redis_client = await self.redis_manager.get_redis()
            await redis_client.ping()
            logger.info("Successfully connected to Redis")
            storage_backend = self.redis_manager
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Falling back to in-memory session storage")
            self.redis_manager = None
            storage_backend = InMemorySessionStorage()
        
        # Initialize session manager with longer timeout to prevent immediate expiration
        self.session_manager = SessionManager(storage_backend, session_timeout_minutes=120)  # 2 hours
        self.orchestrator = ConversationGraphOrchestrator(self.session_manager)
        
        # Setup internal API client
        self.api_base_url = getattr(settings, 'API_BASE_URL', 'http://localhost:8000')
        self.internal_client = httpx.AsyncClient(
            base_url=self.api_base_url,
            timeout=30.0
        )
        
        logger.info("EnhancedConversationService initialized successfully")

    async def process_message(
        self, 
        session_id: str, 
        user_message: str, 
        user_id: str, 
        form_template_id: str = None,
        user_token: str = None
    ) -> str:
        """Process user message with enhanced session handling and response extraction."""

        logger.info(f"📍 SERVICE: ENTRY - process_message called with session_id='{session_id}', user_message='{user_message}', user_id='{user_id}'")

        try:
            # Enhanced session retrieval with detailed logging
            session_data = await self._get_or_create_session(session_id, user_id, form_template_id)
            if not session_data:
                logger.error(f"Failed to get or create session {session_id}")
                return "I'm sorry, but I encountered an issue with your session. Please try starting a new conversation."

            # Validate user access if needed
            target_form_id = form_template_id or getattr(session_data, 'form_template_id', None)
            if target_form_id and target_form_id.strip() != "" and user_token:
                has_access = await self._validate_user_access(user_id, target_form_id, user_token)
                if not has_access:
                    return "You don't have permission to access that form. Please contact your administrator."

            # Prepare initial state with enhanced metadata
            # Ensure form_template_id is properly handled (can be empty string if not set)
            effective_form_template_id = session_data.form_template_id or form_template_id or ""
            
            initial_state = {
                "session_id": session_id,
                "user_id": user_id,
                "user_message": user_message,
                "form_template_id": effective_form_template_id,
                "user_token": user_token,
                "api_client": self.internal_client,
                "session_state": session_data.state.value if isinstance(session_data.state, SessionState) else session_data.state,
                "conversation_history": getattr(session_data, 'conversation_history', []),
                # Initialize other fields that may be expected by the graph
                "current_field": None,
                "responses": getattr(session_data, 'responses', {}),
                "completed_fields": [],
                "missing_required_fields": getattr(session_data, 'missing_required_fields', []),
                "chat_history": getattr(session_data, 'conversation_history', []),
                "state": getattr(session_data, 'state', SessionState.STARTING).value if isinstance(getattr(session_data, 'state', SessionState.STARTING), SessionState) else getattr(session_data, 'state', SessionState.STARTING),
                "is_complete": False,
                "final_response": None,
                "error_message": None,
                "next_node": None
            }

            logger.info(f"🔍 ECS: Processing message for session {session_id}, state: {initial_state['session_state']}, form_id: {effective_form_template_id}")

            # Invoke orchestrator with error handling
            result_state = await self._invoke_orchestrator_safely(initial_state)
            if not result_state:
                return "I encountered an issue processing your request. Please try again."

            # Enhanced response extraction
            agent_response = self._extract_response_with_fallbacks(result_state)
            
            # Extract additional metadata
            confidence_score = self._safe_get_from_state(result_state, "confidence_score")
            is_complete = self._safe_get_from_state(result_state, "is_complete", False)
            
            # Log conversation with enhanced metadata
            await self._log_enhanced_conversation_turn(
                session_id, "user", user_message, _normalize_state(initial_state), confidence_score
            )
            
            await self._log_enhanced_conversation_turn(
                session_id, "agent", agent_response, _normalize_state(result_state), confidence_score, is_complete
            )

            # Validate response before returning
            if not agent_response or agent_response.strip() == "":
                logger.warning(f"Empty response extracted for session {session_id}")
                return self._get_fallback_response(result_state)
            
            return agent_response

        except Exception as e:
            logger.exception(f"Error processing message for session {session_id}: {e}")
            await self._log_error_turn(session_id, str(e))
            return "I encountered an unexpected error. Please try again, and contact support if the problem persists."

    async def _get_or_create_session(self, session_id: str, user_id: str, form_template_id: str = None) -> SessionData:
        """Lazy session retrieval with minimal upfront creation."""

        # Try to get existing session
        session_data = await self.session_manager.get_session(session_id)

        if session_data:
            logger.info(f"Retrieved existing session {session_id}, state: {session_data.state}")
            # Update last activity to prevent timeout (async, don't wait)
            session_data.last_activity = datetime.utcnow()
            # Fire and forget - don't wait for save to complete
            _ = asyncio.create_task(self.session_manager.save_session(session_data))
            return session_data

        # Lazy session creation - create minimal session object
        logger.info(f"Creating lazy session {session_id} for user {user_id}")

        current_time = datetime.utcnow()
        session_data = SessionData(
            session_id=session_id,
            user_id=user_id,
            form_template_id=form_template_id or "",
            created_at=current_time,
            last_activity=current_time,
            state=SessionState.STARTING,
            responses={},
            missing_required_fields=[],
            conversation_history=[],
            current_field_index=0,
            field_responses={},
            updated_at=current_time
        )

        # Save session asynchronously (fire and forget for first response speed)
        _ = asyncio.create_task(self._save_session_async(session_data))

        logger.info(f"Created lazy session {session_id}")
        return session_data

    async def _save_session_async(self, session_data: SessionData):
        """Save session asynchronously without blocking the main flow."""
        try:
            await self.session_manager.save_session(session_data)
            logger.debug(f"Successfully saved session {session_data.session_id}")
        except Exception as e:
            logger.error(f"Failed to save session {session_data.session_id}: {e}")

    async def _invoke_orchestrator_safely(self, initial_state: dict) -> dict:
        """Safely invoke orchestrator with enhanced error handling."""
        try:
            logger.info(f"🔍 SERVICE: Invoking orchestrator with state keys: {list(initial_state.keys())}")
            logger.info(f"📍 SERVICE: STATE PREPARED - user_message='{initial_state.get('user_message')}', session_id='{initial_state.get('session_id')}', user_id='{initial_state.get('user_id')}'")

            logger.info(f"📍 SERVICE: About to call orchestrator.invoke() with session_id='{initial_state.get('session_id')}'")
            # Execute the conversation graph
            result_state = await self.orchestrator.invoke(initial_state)
            logger.info(f"📍 SERVICE: Orchestrator returned, final_state session_id='{result_state.get('session_id') if result_state else None}'")
            
            if not result_state:
                logger.error("Orchestrator returned None or empty result")
                return {"final_response": "I'm having trouble processing your request right now. Please try again."}
            
            logger.info(f"Orchestrator completed successfully, result type: {type(result_state)}")
            return result_state
            
        except Exception as e:
            logger.exception(f"Error in orchestrator invocation: {e}")
            return {
                "final_response": "I encountered an issue while processing your request. Please try again.",
                "error_message": str(e)
            }

    def _extract_response_with_fallbacks(self, result_state) -> str:
        """Enhanced response extraction with comprehensive fallback logic."""
        
        if not result_state:
            logger.warning("Result state is None or empty")
            return ""
        
        # Log state structure for debugging
        logger.debug(f"Extracting response from state type: {type(result_state)}")
        if isinstance(result_state, dict):
            logger.debug(f"Available keys: {list(result_state.keys())}")
        
        # Priority order for response extraction
        response_keys = [
            "final_response", 
            "response", 
            "message", 
            "output",
            "content",
            "text",
            "reply"
        ]
        
        # Method 1: Direct dictionary access
        if isinstance(result_state, dict):
            for key in response_keys:
                value = result_state.get(key)
                if value and str(value).strip():  # Check for non-empty strings
                    logger.debug(f"Found response using key '{key}': {value[:100]}...")
                    return str(value).strip()
        
        # Method 2: Object attribute access
        for key in response_keys:
            if hasattr(result_state, key):
                value = getattr(result_state, key, None)
                if value and str(value).strip():
                    logger.debug(f"Found response using attribute '{key}': {value[:100]}...")
                    return str(value).strip()
        
        # Method 3: Nested state exploration
        if isinstance(result_state, dict):
            nested_keys = ["state", "graph_state", "final_state", "current_state", "data"]
            for nested_key in nested_keys:
                nested_obj = result_state.get(nested_key)
                if nested_obj:
                    nested_response = self._extract_from_nested_object(nested_obj, response_keys)
                    if nested_response:
                        logger.debug(f"Found response in nested object '{nested_key}': {nested_response[:100]}...")
                        return nested_response
        
        # Method 4: Check for clarification messages
        clarification_keys = ["clarification_message", "clarification", "help_message"]
        if isinstance(result_state, dict):
            for key in clarification_keys:
                value = result_state.get(key)
                if value and str(value).strip():
                    logger.debug(f"Found clarification using key '{key}': {value[:100]}...")
                    return str(value).strip()
        
        logger.warning(f"No response found in result_state. Keys: {list(result_state.keys()) if isinstance(result_state, dict) else 'N/A'}")
        return ""

    def _extract_from_nested_object(self, nested_obj, response_keys) -> str:
        """Extract response from nested object structures."""
        try:
            # Convert to dict if it's a Pydantic model
            if hasattr(nested_obj, 'model_dump'):
                nested_dict = nested_obj.model_dump()
            elif hasattr(nested_obj, 'dict'):
                nested_dict = nested_obj.dict()
            elif isinstance(nested_obj, dict):
                nested_dict = nested_obj
            else:
                nested_dict = vars(nested_obj) if hasattr(nested_obj, '__dict__') else {}
            
            # Search for response in nested dict
            for key in response_keys:
                value = nested_dict.get(key)
                if value and str(value).strip():
                    return str(value).strip()
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error extracting from nested object: {e}")
            return ""

    def _get_fallback_response(self, result_state) -> str:
        """Generate appropriate fallback response based on state."""
        
        # Check for error messages
        if isinstance(result_state, dict):
            error_msg = result_state.get('error_message') or result_state.get('error')
            if error_msg:
                return f"I encountered an issue: {error_msg}"
            
            # Check if this is a clarification scenario
            if result_state.get('requires_clarification'):
                return "I need more information to help you. Could you please provide more details about what you're looking for?"
            
            # Check completion status
            if result_state.get('is_complete'):
                return "Thank you! I've completed processing your request."
        
        # Generic fallback
        return "I'm having trouble generating a response right now. Could you please try rephrasing your request?"

    def _safe_get_from_state(self, state, key, default=None):
        """Safely extract values from state object."""
        if isinstance(state, dict):
            return state.get(key, default)
        return getattr(state, key, default)

    async def _log_enhanced_conversation_turn(
        self, 
        session_id: str, 
        actor: str, 
        message: str, 
        state_data: dict, 
        confidence_score: float = None,
        is_complete: bool = None
    ):
        """Enhanced conversation logging with comprehensive metadata."""
        try:
            # Enrich state with metadata
            enriched_state = dict(state_data) if state_data else {}
            enriched_state.update({
                'timestamp': datetime.utcnow().isoformat(),
                'actor': actor,
                'message_length': len(message) if message else 0
            })
            
            if confidence_score is not None:
                enriched_state['confidence_score'] = confidence_score
            if is_complete is not None:
                enriched_state['is_complete'] = is_complete
            
            log_entry = ConversationLog(
                session_id=session_id,
                actor=actor,
                message=message or "",
                state_at_turn=json.dumps(enriched_state, default=str)
            )
            
            await self.db.conversation_logs.insert_one(log_entry.model_dump(by_alias=True))
            logger.debug(f"Successfully logged {actor} turn for session {session_id}")
            
        except Exception as log_exc:
            logger.exception(f"Failed to log conversation turn for session {session_id}: {log_exc}")

    async def _log_error_turn(self, session_id: str, error_message: str):
        """Log error turns with appropriate metadata."""
        try:
            error_state = {
                "error": error_message,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": "processing_error"
            }
            
            await self._log_enhanced_conversation_turn(
                session_id, "system", f"Error: {error_message}", error_state
            )
        except Exception as log_error:
            logger.error(f"Failed to log error turn: {log_error}")

    # Keep existing API methods with enhanced error handling
    async def _get_form_via_api(self, form_id: str, user_token: str) -> Dict[str, Any]:
        """Fetch form template via internal API call."""
        try:
            headers = {"Authorization": f"Bearer {user_token}"}
            response = await self.internal_client.get(
                f"/forms-management/templates/{form_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch form {form_id} via API: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching form via API: {e}")
            return None

    async def _get_context_via_api(self, context_id: str, user_token: str) -> Dict[str, Any]:
        """Fetch context information via internal API call."""
        try:
            headers = {"Authorization": f"Bearer {user_token}"}
            response = await self.internal_client.get(
                f"/forms-management/contexts/{context_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch context {context_id} via API: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching context via API: {e}")
            return None

    async def _validate_user_access(self, user_id: str, form_id: str, user_token: str) -> bool:
        """Validate user has access to the specified form via API."""
        try:
            form_data = await self._get_form_via_api(form_id, user_token)
            if not form_data:
                # If form doesn't exist, allow access to avoid blocking users
                # The system will handle missing forms gracefully
                logger.warning(f"Form {form_id} not found, allowing access")
                return True
            
            # Check if form is public (no context_id means it's a general form)
            context_id = form_data.get('context_id')
            if not context_id:
                # If there's no context, this might be a public form - allow access
                return True
            
            context_data = await self._get_context_via_api(context_id, user_token)
            if not context_data:
                # If context doesn't exist, allow access to avoid blocking users
                logger.warning(f"Context {context_id} not found for form {form_id}, allowing access")
                return True
            
            # For private contexts, check access permissions
            user_has_access = (
                context_data.get('created_by') == user_id or
                user_id in context_data.get('assigned_users', []) or
                user_id in context_data.get('assigned_professionals', [])
            )
            
            # If not in the specific lists, check if the form has public access setting
            if not user_has_access:
                # Check if form is marked as public access
                form_is_public = form_data.get('public', False)
                if form_is_public:
                    return True
            
            return user_has_access
            
        except Exception as e:
            logger.error(f"Error validating user access: {e}")
            # In case of error, be permissive to avoid blocking users
            return True

    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve conversation history with enhanced error handling."""
        try:
            # Try session manager first
            session_data = await self.session_manager.get_session(session_id)
            if session_data and hasattr(session_data, 'conversation_history'):
                return session_data.conversation_history[-limit:]
            
            # Fallback to database
            cursor = self.db.conversation_logs.find(
                {"session_id": session_id}
            ).sort("created_at", 1).limit(limit)
            
            history = []
            async for log in cursor:
                history.append({
                    "role": log["actor"],
                    "message": log["message"],
                    "timestamp": log.get("created_at"),
                    "metadata": json.loads(log.get("state_at_turn", "{}"))
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []

    async def cleanup(self):
        """Cleanup resources."""
        try:
            if hasattr(self, 'internal_client'):
                await self.internal_client.aclose()
            if hasattr(self, 'session_manager'):
                await self.session_manager.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Singleton instance
enhanced_conversation_service = EnhancedConversationService()
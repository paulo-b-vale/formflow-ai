"""
Agent Service - The routing/management layer for all AI agents.

This service is responsible for:
1. Selecting the appropriate agent based on user intent or explicit request
2. Managing agent lifecycle and state
3. Providing a unified interface for agent invocation
4. Handling async agent execution via Celery (future)
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, Field

from app.services.base_service import BaseService
from app.agents.orchestrator import ConversationGraphOrchestrator
from app.agents.registry import agent_registry, AgentCapability, ProcessingMode
from app.sessions.session_manager import SessionManager, SessionData, SessionState
from app.database import db

logger = logging.getLogger(__name__)


class AgentInvocationRequest(BaseModel):
    """Request to invoke an agent"""
    session_id: str
    user_id: str
    user_message: str
    agent_id: Optional[str] = None  # If None, auto-select agent
    context: Optional[Dict[str, Any]] = None
    force_async: bool = False  # Force async processing even for sync agents


class AgentInvocationResponse(BaseModel):
    """Response from agent invocation"""
    success: bool
    response: str
    agent_id: str
    agent_name: str
    processing_mode: ProcessingMode
    task_id: Optional[str] = None  # For async operations
    metadata: Dict[str, Any] = {}
    confidence: Optional[float] = None
    next_suggested_agent: Optional[str] = None


class AgentService(BaseService):
    """
    Agent Service - Routes requests to appropriate agents.

    This is the main entry point for all agent interactions.
    Think of it as a smart router that decides which agent should handle each request.
    """

    def __init__(self):
        super().__init__()
        self.session_manager: Optional[SessionManager] = None
        self.orchestrator: Optional[ConversationGraphOrchestrator] = None
        self._agent_stats: Dict[str, Dict[str, Any]] = {}  # Track agent usage

    async def initialize(self):
        """Initialize the agent service"""
        await super().initialize()

        # Initialize session manager
        from app.sessions.session_manager import RedisManager
        try:
            redis_manager = RedisManager()
            await redis_manager.get_redis()
            self.session_manager = SessionManager(redis_manager, session_timeout_minutes=120)
            logger.info("AgentService: Session manager initialized with Redis")
        except Exception as e:
            logger.error(f"AgentService: Redis initialization failed: {e}")
            from app.sessions.session_manager import InMemorySessionStorage
            storage = InMemorySessionStorage()
            self.session_manager = SessionManager(storage, session_timeout_minutes=120)
            logger.info("AgentService: Using in-memory session storage")

        # Initialize orchestrator (for backward compatibility with graph-based routing)
        self.orchestrator = ConversationGraphOrchestrator(self.session_manager)

        logger.info("AgentService initialized successfully")

    async def invoke_agent(
        self,
        request: AgentInvocationRequest
    ) -> AgentInvocationResponse:
        """
        Main entry point for agent invocation.

        Args:
            request: Agent invocation request

        Returns:
            Agent invocation response
        """
        logger.info(
            f"AgentService: Invoke request - session={request.session_id}, "
            f"agent={request.agent_id or 'AUTO'}, message='{request.user_message[:50]}...'"
        )

        # Step 1: Get or create session
        session_data = await self._get_or_create_session(
            request.session_id,
            request.user_id,
            request.context
        )

        # Step 2: Determine which agent to use
        if request.agent_id:
            # Explicit agent selection
            agent_metadata = agent_registry.get_agent(request.agent_id)
            if not agent_metadata:
                return AgentInvocationResponse(
                    success=False,
                    response=f"Agent '{request.agent_id}' not found",
                    agent_id=request.agent_id or "unknown",
                    agent_name="Unknown",
                    processing_mode=ProcessingMode.SYNC
                )
            agent_id = request.agent_id
        else:
            # Auto-select agent based on intent
            agent_id = await self._select_agent(request.user_message, session_data, request.context)

        agent_metadata = agent_registry.get_agent(agent_id)
        if not agent_metadata:
            # Fallback to orchestrator if no agent found
            return await self._invoke_orchestrator_fallback(request, session_data)

        logger.info(f"AgentService: Selected agent '{agent_id}' ({agent_metadata.name})")

        # Step 3: Check if agent should run async
        should_run_async = (
            request.force_async or
            agent_metadata.processing_mode == ProcessingMode.ASYNC
        )

        if should_run_async:
            # Queue for async processing (Celery task)
            return await self._invoke_agent_async(agent_id, request, session_data)
        else:
            # Execute synchronously
            return await self._invoke_agent_sync(agent_id, request, session_data)

    async def _select_agent(
        self,
        user_message: str,
        session_data: SessionData,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Automatically select the best agent for this request.

        This is where the "routing intelligence" lives.
        You can make this as simple or complex as needed.
        """
        # Option 1: Simple keyword-based routing (fast, deterministic)
        recommended = agent_registry.get_recommended_agent(user_message, context)
        if recommended:
            logger.debug(f"Keyword-based routing selected: {recommended}")
            return recommended

        # Option 2: State-based routing
        # If we're in the middle of form filling, keep using form_filler
        if session_data.state == SessionState.IN_PROGRESS:
            if session_data.form_template_id:
                logger.debug("State-based routing: continuing form_filler")
                return "form_filler"

        # Option 3: LLM-based routing (slower, more flexible)
        # TODO: Use a lightweight LLM call to classify intent
        # For now, fallback to router node

        return "router"  # Default to router agent

    async def _invoke_agent_sync(
        self,
        agent_id: str,
        request: AgentInvocationRequest,
        session_data: SessionData
    ) -> AgentInvocationResponse:
        """Execute agent synchronously"""
        agent_metadata = agent_registry.get_agent(agent_id)

        try:
            # Prepare agent input
            agent_input = {
                "session_id": request.session_id,
                "user_id": request.user_id,
                "user_message": request.user_message,
                "session_data": session_data,
                "context": request.context or {},
            }

            # Get agent processor
            processor = agent_registry.get_processor(agent_id)
            if processor:
                # Direct processor invocation
                result = await processor(agent_input)
            else:
                # Fallback to orchestrator
                result = await self._invoke_via_orchestrator(agent_id, agent_input)

            # Track usage
            self._track_agent_usage(agent_id, success=True)

            # Extract response
            response_text = self._extract_response(result)
            confidence = result.get("confidence_score") if isinstance(result, dict) else None

            return AgentInvocationResponse(
                success=True,
                response=response_text,
                agent_id=agent_id,
                agent_name=agent_metadata.name,
                processing_mode=agent_metadata.processing_mode,
                metadata=result if isinstance(result, dict) else {},
                confidence=confidence
            )

        except Exception as e:
            logger.exception(f"Error invoking agent {agent_id}: {e}")
            self._track_agent_usage(agent_id, success=False)

            return AgentInvocationResponse(
                success=False,
                response=f"Agent execution failed: {str(e)}",
                agent_id=agent_id,
                agent_name=agent_metadata.name,
                processing_mode=agent_metadata.processing_mode
            )

    async def _invoke_agent_async(
        self,
        agent_id: str,
        request: AgentInvocationRequest,
        session_data: SessionData
    ) -> AgentInvocationResponse:
        """Queue agent for async execution via Celery"""
        agent_metadata = agent_registry.get_agent(agent_id)

        # TODO: Implement Celery task queuing
        # For now, return a placeholder
        logger.warning(f"Async execution requested for {agent_id} but not yet implemented")

        # Temporary: Fall back to sync execution
        return await self._invoke_agent_sync(agent_id, request, session_data)

    async def _invoke_orchestrator_fallback(
        self,
        request: AgentInvocationRequest,
        session_data: SessionData
    ) -> AgentInvocationResponse:
        """
        Fallback to the existing orchestrator for backward compatibility.
        This allows us to gradually migrate agents to the new system.
        """
        logger.info("AgentService: Using orchestrator fallback")

        initial_state = {
            "session_id": request.session_id,
            "user_id": request.user_id,
            "user_message": request.user_message,
            "form_template_id": session_data.form_template_id or "",
            "session_state": session_data.state.value if isinstance(session_data.state, SessionState) else session_data.state,
            "conversation_history": session_data.conversation_history,
            "responses": session_data.responses,
            "context": request.context or {},
        }

        try:
            result_state = await self.orchestrator.invoke(initial_state)
            response_text = self._extract_response(result_state)

            return AgentInvocationResponse(
                success=True,
                response=response_text,
                agent_id="orchestrator",
                agent_name="Graph Orchestrator",
                processing_mode=ProcessingMode.SYNC,
                metadata=result_state if isinstance(result_state, dict) else {}
            )

        except Exception as e:
            logger.exception(f"Orchestrator fallback failed: {e}")
            return AgentInvocationResponse(
                success=False,
                response=f"I encountered an error processing your request: {str(e)}",
                agent_id="orchestrator",
                agent_name="Graph Orchestrator",
                processing_mode=ProcessingMode.SYNC
            )

    async def _invoke_via_orchestrator(
        self,
        agent_id: str,
        agent_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke agent via the orchestrator (legacy compatibility)"""
        # Build state for orchestrator
        state = {
            **agent_input,
            "next_node": agent_id,  # Tell orchestrator which node to use
        }

        return await self.orchestrator.invoke(state)

    def _extract_response(self, result: Any) -> str:
        """Extract text response from agent result"""
        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            # Try common response keys
            for key in ["final_response", "response", "message", "output", "content"]:
                if key in result and result[key]:
                    return str(result[key])

        if hasattr(result, "final_response"):
            return str(result.final_response)

        return "Agent processed your request successfully."

    async def _get_or_create_session(
        self,
        session_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SessionData:
        """Get or create a session"""
        session_data = await self.session_manager.get_session(session_id)

        if session_data:
            session_data.last_activity = datetime.utcnow()
            return session_data

        # Create new session
        form_template_id = context.get("form_template_id") if context else None

        session_data = SessionData(
            session_id=session_id,
            user_id=user_id,
            form_template_id=form_template_id or "",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            state=SessionState.STARTING,
            responses={},
            missing_required_fields=[],
            conversation_history=[],
            current_field_index=0,
            field_responses={},
            updated_at=datetime.utcnow()
        )

        await self.session_manager.save_session(session_data)
        return session_data

    def _track_agent_usage(self, agent_id: str, success: bool):
        """Track agent usage statistics"""
        if agent_id not in self._agent_stats:
            self._agent_stats[agent_id] = {
                "total_invocations": 0,
                "successful_invocations": 0,
                "failed_invocations": 0,
                "last_invoked": None
            }

        stats = self._agent_stats[agent_id]
        stats["total_invocations"] += 1
        if success:
            stats["successful_invocations"] += 1
        else:
            stats["failed_invocations"] += 1
        stats["last_invoked"] = datetime.utcnow().isoformat()

    def get_agent_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get agent usage statistics"""
        if agent_id:
            return self._agent_stats.get(agent_id, {})
        return self._agent_stats

    async def list_available_agents(
        self,
        capability: Optional[AgentCapability] = None,
        processing_mode: Optional[ProcessingMode] = None
    ) -> List[Dict[str, Any]]:
        """
        List all available agents with their capabilities.
        This is useful for building UIs or debugging.
        """
        agents = agent_registry.list_agents(
            capability=capability,
            processing_mode=processing_mode
        )

        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": [c.value for c in agent.capabilities],
                "processing_mode": agent.processing_mode.value,
                "requires_auth": agent.requires_auth,
                "estimated_duration_ms": agent.estimated_duration_ms,
                "stats": self._agent_stats.get(agent.agent_id, {})
            }
            for agent in agents
        ]

    async def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific agent"""
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            return None

        schema = agent_registry.get_agent_schema(agent_id)
        stats = self._agent_stats.get(agent_id, {})

        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "description": agent.description,
            "version": agent.version,
            "capabilities": [c.value for c in agent.capabilities],
            "processing_mode": agent.processing_mode.value,
            "requires_auth": agent.requires_auth,
            "requires_form_context": agent.requires_form_context,
            "estimated_duration_ms": agent.estimated_duration_ms,
            "cost_per_invocation": agent.cost_per_invocation,
            "input_schema": schema.get("input_schema") if schema else None,
            "output_schema": schema.get("output_schema") if schema else None,
            "examples": agent.examples,
            "tags": agent.tags,
            "stats": stats
        }


# Singleton instance
agent_service = AgentService()


# Backward compatibility wrapper
class EnhancedConversationService:
    """
    Backward compatibility wrapper.
    This maintains the old API while delegating to the new AgentService.
    """

    def __init__(self):
        self._agent_service = agent_service

    async def initialize(self):
        await self._agent_service.initialize()

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        user_id: str,
        form_template_id: str = None,
        user_token: str = None,
        file_ids: Optional[List[str]] = None
    ) -> str:
        """Legacy API - delegates to AgentService"""
        context = {}
        if form_template_id:
            context["form_template_id"] = form_template_id
        if user_token:
            context["user_token"] = user_token
        if file_ids:
            context["file_ids"] = file_ids

        request = AgentInvocationRequest(
            session_id=session_id,
            user_id=user_id,
            user_message=user_message,
            context=context
        )

        response = await self._agent_service.invoke_agent(request)
        return response.response


# Export both for compatibility
enhanced_conversation_service = EnhancedConversationService()

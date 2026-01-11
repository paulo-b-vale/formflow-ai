"""
Agent Registry - MCP-style service discovery and introspection.
Provides a centralized registry for all agents with metadata, capabilities, and schemas.
"""

from typing import Dict, List, Optional, Type, Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import inspect
import logging

logger = logging.getLogger(__name__)


class AgentCapability(str, Enum):
    """Agent capability types"""
    FORM_PREDICTION = "form_prediction"
    FORM_FILLING = "form_filling"
    REPORT_GENERATION = "report_generation"
    FORM_SEARCH = "form_search"
    CLARIFICATION = "clarification"
    INTENT_ROUTING = "intent_routing"
    DATA_EXTRACTION = "data_extraction"
    VALIDATION = "validation"
    ERROR_HANDLING = "error_handling"


class ProcessingMode(str, Enum):
    """How the agent processes requests"""
    SYNC = "sync"  # Returns immediately
    ASYNC = "async"  # Returns task ID, poll for result
    STREAMING = "streaming"  # SSE/WebSocket stream


class AgentInputSchema(BaseModel):
    """Base schema for agent inputs"""
    session_id: str = Field(..., description="Session identifier")
    user_message: str = Field(..., description="User's input message")
    user_id: str = Field(..., description="User identifier")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")


class AgentOutputSchema(BaseModel):
    """Base schema for agent outputs"""
    success: bool = Field(..., description="Whether operation succeeded")
    response: str = Field(..., description="Agent's response message")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")
    next_action: Optional[str] = Field(None, description="Suggested next action")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")


class AgentMetadata(BaseModel):
    """Metadata describing an agent's capabilities and interface"""
    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="What this agent does")
    version: str = Field(default="1.0.0", description="Agent version")
    capabilities: List[AgentCapability] = Field(..., description="What this agent can do")
    processing_mode: ProcessingMode = Field(default=ProcessingMode.SYNC, description="Processing mode")

    # Schemas
    input_schema: Type[BaseModel] = Field(..., description="Expected input schema")
    output_schema: Type[BaseModel] = Field(..., description="Output schema")

    # Configuration
    requires_auth: bool = Field(default=True, description="Whether auth is required")
    requires_form_context: bool = Field(default=False, description="Whether form context is needed")
    max_retries: int = Field(default=3, description="Max retry attempts")
    timeout_seconds: int = Field(default=30, description="Processing timeout")

    # Cost/Performance
    estimated_duration_ms: int = Field(default=1000, description="Est. processing time")
    cost_per_invocation: Optional[float] = Field(None, description="Cost in credits/tokens")

    # Documentation
    examples: List[Dict[str, Any]] = Field(default=[], description="Usage examples")
    tags: List[str] = Field(default=[], description="Searchable tags")

    class Config:
        arbitrary_types_allowed = True


class AgentRegistry:
    """
    Centralized registry for agent discovery and management.
    Provides MCP-style service introspection and routing.
    """

    def __init__(self):
        self._agents: Dict[str, AgentMetadata] = {}
        self._agent_instances: Dict[str, Any] = {}
        self._processors: Dict[str, Callable] = {}
        logger.info("AgentRegistry initialized")

    def register(
        self,
        agent_id: str,
        metadata: AgentMetadata,
        agent_instance: Any = None,
        processor: Optional[Callable] = None
    ):
        """
        Register an agent with the registry.

        Args:
            agent_id: Unique identifier
            metadata: Agent metadata and capabilities
            agent_instance: Optional agent class instance
            processor: Optional async function to process requests
        """
        if agent_id in self._agents:
            logger.warning(f"Agent {agent_id} already registered, overwriting")

        self._agents[agent_id] = metadata

        if agent_instance:
            self._agent_instances[agent_id] = agent_instance

        if processor:
            self._processors[agent_id] = processor

        logger.info(f"Registered agent: {agent_id} ({metadata.name})")

    def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """Get agent metadata by ID"""
        return self._agents.get(agent_id)

    def get_agent_instance(self, agent_id: str) -> Optional[Any]:
        """Get agent instance by ID"""
        return self._agent_instances.get(agent_id)

    def get_processor(self, agent_id: str) -> Optional[Callable]:
        """Get agent processor function by ID"""
        return self._processors.get(agent_id)

    def list_agents(
        self,
        capability: Optional[AgentCapability] = None,
        tags: Optional[List[str]] = None,
        processing_mode: Optional[ProcessingMode] = None
    ) -> List[AgentMetadata]:
        """
        List agents with optional filtering.

        Args:
            capability: Filter by capability
            tags: Filter by tags
            processing_mode: Filter by processing mode

        Returns:
            List of matching agent metadata
        """
        results = list(self._agents.values())

        if capability:
            results = [a for a in results if capability in a.capabilities]

        if tags:
            results = [a for a in results if any(tag in a.tags for tag in tags)]

        if processing_mode:
            results = [a for a in results if a.processing_mode == processing_mode]

        return results

    def search_agents(self, query: str) -> List[AgentMetadata]:
        """
        Search agents by query string (name, description, tags).

        Args:
            query: Search query

        Returns:
            List of matching agents
        """
        query_lower = query.lower()
        results = []

        for metadata in self._agents.values():
            if (
                query_lower in metadata.name.lower() or
                query_lower in metadata.description.lower() or
                any(query_lower in tag.lower() for tag in metadata.tags)
            ):
                results.append(metadata)

        return results

    def get_agent_schema(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get JSON schema for agent's input/output.

        Args:
            agent_id: Agent identifier

        Returns:
            Dict with input_schema and output_schema
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return None

        return {
            "agent_id": agent_id,
            "input_schema": agent.input_schema.model_json_schema(),
            "output_schema": agent.output_schema.model_json_schema(),
            "examples": agent.examples
        }

    def get_recommended_agent(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Recommend the best agent for a given user message.
        (Simple keyword-based routing - can be enhanced with ML)

        Args:
            user_message: User's input
            context: Optional context

        Returns:
            Recommended agent_id or None
        """
        message_lower = user_message.lower()

        # Simple keyword-based routing
        if any(word in message_lower for word in ["report", "generate", "analysis", "summary"]):
            return self._find_agent_by_capability(AgentCapability.REPORT_GENERATION)

        if any(word in message_lower for word in ["search", "find", "look for", "which form"]):
            return self._find_agent_by_capability(AgentCapability.FORM_SEARCH)

        if any(word in message_lower for word in ["fill", "complete", "answer", "submit"]):
            return self._find_agent_by_capability(AgentCapability.FORM_FILLING)

        # Default to router
        return self._find_agent_by_capability(AgentCapability.INTENT_ROUTING)

    def _find_agent_by_capability(self, capability: AgentCapability) -> Optional[str]:
        """Find first agent with given capability"""
        for agent_id, metadata in self._agents.items():
            if capability in metadata.capabilities:
                return agent_id
        return None

    def validate_input(self, agent_id: str, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input against agent's schema.

        Args:
            agent_id: Agent identifier
            input_data: Input data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return False, f"Agent {agent_id} not found"

        try:
            agent.input_schema(**input_data)
            return True, None
        except Exception as e:
            return False, str(e)

    def get_capabilities_map(self) -> Dict[AgentCapability, List[str]]:
        """
        Get mapping of capabilities to agent IDs.

        Returns:
            Dict mapping each capability to list of agent IDs
        """
        capabilities_map: Dict[AgentCapability, List[str]] = {}

        for agent_id, metadata in self._agents.items():
            for capability in metadata.capabilities:
                if capability not in capabilities_map:
                    capabilities_map[capability] = []
                capabilities_map[capability].append(agent_id)

        return capabilities_map


# Global registry instance
agent_registry = AgentRegistry()


def register_agent(
    agent_id: str,
    name: str,
    description: str,
    capabilities: List[AgentCapability],
    input_schema: Type[BaseModel] = AgentInputSchema,
    output_schema: Type[BaseModel] = AgentOutputSchema,
    **kwargs
):
    """
    Decorator to register an agent.

    Usage:
        @register_agent(
            agent_id="form_filler",
            name="Form Filler Agent",
            description="Guides users through form completion",
            capabilities=[AgentCapability.FORM_FILLING]
        )
        async def process_form_filling(state: dict):
            ...
    """
    def decorator(func_or_class):
        metadata = AgentMetadata(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities,
            input_schema=input_schema,
            output_schema=output_schema,
            **kwargs
        )

        # Register with processor if it's a function
        if inspect.iscoroutinefunction(func_or_class):
            agent_registry.register(agent_id, metadata, processor=func_or_class)
        else:
            # It's a class, register metadata only
            agent_registry.register(agent_id, metadata, agent_instance=func_or_class)

        return func_or_class

    return decorator

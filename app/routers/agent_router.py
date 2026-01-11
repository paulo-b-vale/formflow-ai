"""
Agent Router - API endpoints for explicit agent interaction.

This allows users/developers to:
1. List available agents
2. Get agent details and schemas
3. Invoke specific agents directly
4. Query agent capabilities
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from app.services.agent_service import agent_service, AgentInvocationRequest, AgentInvocationResponse
from app.agents.registry import agent_registry, AgentCapability, ProcessingMode
from app.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models

class MessageRequest(BaseModel):
    """Request to send a message (can specify agent or auto-route)"""
    session_id: str = Field(..., description="Session identifier")
    message: str = Field(..., description="User's message", min_length=1)
    agent_id: Optional[str] = Field(None, description="Specific agent to use (optional)")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")
    force_async: bool = Field(default=False, description="Force async processing")


class MessageResponse(BaseModel):
    """Response from message processing"""
    success: bool
    response: str
    agent_id: str
    agent_name: str
    processing_mode: str
    task_id: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = {}


class AgentListItem(BaseModel):
    """Agent list item"""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    processing_mode: str
    estimated_duration_ms: int


class AgentDetail(BaseModel):
    """Detailed agent information"""
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: List[str]
    processing_mode: str
    requires_auth: bool
    requires_form_context: bool
    estimated_duration_ms: int
    cost_per_invocation: Optional[float]
    input_schema: Optional[Dict[str, Any]]
    output_schema: Optional[Dict[str, Any]]
    examples: List[Dict[str, Any]]
    tags: List[str]
    stats: Dict[str, Any]


# Endpoints

@router.post("/message", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a message to an agent (auto-routed or explicit).

    This is the main entry point for agent interactions.

    **Auto-routing example:**
    ```json
    {
        "session_id": "user-123",
        "message": "I need to fill out a form"
    }
    ```

    **Explicit agent example:**
    ```json
    {
        "session_id": "user-123",
        "message": "Generate a report",
        "agent_id": "report_generator"
    }
    ```

    **With context:**
    ```json
    {
        "session_id": "user-123",
        "message": "Fill this form",
        "context": {
            "form_template_id": "507f1f77bcf86cd799439011"
        }
    }
    ```
    """
    try:
        user_id = current_user["_id"]

        # Create agent invocation request
        agent_request = AgentInvocationRequest(
            session_id=request.session_id,
            user_id=user_id,
            user_message=request.message,
            agent_id=request.agent_id,
            context=request.context,
            force_async=request.force_async
        )

        # Invoke agent
        response = await agent_service.invoke_agent(agent_request)

        return MessageResponse(
            success=response.success,
            response=response.response,
            agent_id=response.agent_id,
            agent_name=response.agent_name,
            processing_mode=response.processing_mode.value,
            task_id=response.task_id,
            confidence=response.confidence,
            metadata=response.metadata
        )

    except Exception as e:
        logger.exception(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=List[AgentListItem])
async def list_agents(
    capability: Optional[str] = Query(None, description="Filter by capability"),
    processing_mode: Optional[str] = Query(None, description="Filter by processing mode"),
    current_user: dict = Depends(get_current_user)
):
    """
    List all available agents with their capabilities.

    **Query parameters:**
    - `capability`: Filter by capability (e.g., "form_filling", "report_generation")
    - `processing_mode`: Filter by mode ("sync", "async", "streaming")

    **Example:**
    ```
    GET /agents?capability=form_filling&processing_mode=sync
    ```

    **Response:**
    ```json
    [
        {
            "agent_id": "form_filler",
            "name": "Form Filler Agent",
            "description": "Guides users through form completion",
            "capabilities": ["form_filling", "data_extraction"],
            "processing_mode": "sync",
            "estimated_duration_ms": 2000
        }
    ]
    ```
    """
    try:
        capability_enum = AgentCapability(capability) if capability else None
        mode_enum = ProcessingMode(processing_mode) if processing_mode else None

        agents = await agent_service.list_available_agents(
            capability=capability_enum,
            processing_mode=mode_enum
        )

        return [
            AgentListItem(
                agent_id=agent["agent_id"],
                name=agent["name"],
                description=agent["description"],
                capabilities=agent["capabilities"],
                processing_mode=agent["processing_mode"],
                estimated_duration_ms=agent["estimated_duration_ms"]
            )
            for agent in agents
        ]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid filter value: {e}")
    except Exception as e:
        logger.exception(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}", response_model=AgentDetail)
async def get_agent_details(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific agent.

    **Includes:**
    - Full metadata
    - Input/output JSON schemas
    - Usage examples
    - Statistics

    **Example:**
    ```
    GET /agents/form_filler
    ```

    **Response:**
    ```json
    {
        "agent_id": "form_filler",
        "name": "Form Filler Agent",
        "description": "Guides users through form completion",
        "version": "1.0.0",
        "capabilities": ["form_filling", "data_extraction"],
        "processing_mode": "sync",
        "input_schema": { ... },
        "output_schema": { ... },
        "examples": [ ... ],
        "stats": {
            "total_invocations": 150,
            "successful_invocations": 145,
            "failed_invocations": 5
        }
    }
    ```
    """
    try:
        agent_info = await agent_service.get_agent_info(agent_id)

        if not agent_info:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        return AgentDetail(**agent_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting agent details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/schema")
async def get_agent_schema(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get JSON Schema for agent's input and output.

    Useful for:
    - Generating UI forms dynamically
    - Validating requests before sending
    - Understanding what data the agent expects

    **Example:**
    ```
    GET /agents/form_filler/schema
    ```

    **Response:**
    ```json
    {
        "agent_id": "form_filler",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": { "type": "string" },
                "user_message": { "type": "string" },
                ...
            },
            "required": ["session_id", "user_message"]
        },
        "output_schema": { ... },
        "examples": [ ... ]
    }
    ```
    """
    try:
        schema = agent_registry.get_agent_schema(agent_id)

        if not schema:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        return schema

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting agent schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capabilities")
async def get_capabilities_map(
    current_user: dict = Depends(get_current_user)
):
    """
    Get a map of all capabilities and which agents provide them.

    Useful for understanding what the system can do.

    **Example:**
    ```
    GET /capabilities
    ```

    **Response:**
    ```json
    {
        "form_filling": ["form_filler"],
        "report_generation": ["report_generator"],
        "form_search": ["form_searcher"],
        "intent_routing": ["router"]
    }
    ```
    """
    try:
        capabilities = agent_registry.get_capabilities_map()

        return {
            capability.value: agent_ids
            for capability, agent_ids in capabilities.items()
        }

    except Exception as e:
        logger.exception(f"Error getting capabilities map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_agents(
    q: str = Query(..., description="Search query", min_length=1),
    current_user: dict = Depends(get_current_user)
):
    """
    Search for agents by name, description, or tags.

    **Example:**
    ```
    GET /search?q=form
    ```

    **Response:**
    ```json
    [
        {
            "agent_id": "form_filler",
            "name": "Form Filler Agent",
            "description": "Guides users through form completion",
            "relevance_score": 0.95
        }
    ]
    ```
    """
    try:
        agents = agent_registry.search_agents(q)

        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": [c.value for c in agent.capabilities],
                "tags": agent.tags
            }
            for agent in agents
        ]

    except Exception as e:
        logger.exception(f"Error searching agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/invoke")
async def invoke_agent_directly(
    agent_id: str,
    request: MessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Directly invoke a specific agent (bypassing auto-routing).

    This is the same as `/message` but with the agent_id in the path.

    **Example:**
    ```
    POST /agents/form_filler/invoke
    {
        "session_id": "user-123",
        "message": "My name is John and email is john@example.com"
    }
    ```
    """
    try:
        user_id = current_user["_id"]

        agent_request = AgentInvocationRequest(
            session_id=request.session_id,
            user_id=user_id,
            user_message=request.message,
            agent_id=agent_id,  # Explicitly set from path
            context=request.context,
            force_async=request.force_async
        )

        response = await agent_service.invoke_agent(agent_request)

        return MessageResponse(
            success=response.success,
            response=response.response,
            agent_id=response.agent_id,
            agent_name=response.agent_name,
            processing_mode=response.processing_mode.value,
            task_id=response.task_id,
            confidence=response.confidence,
            metadata=response.metadata
        )

    except Exception as e:
        logger.exception(f"Error invoking agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_agent_stats(
    agent_id: Optional[str] = Query(None, description="Specific agent ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get usage statistics for agents.

    **All agents:**
    ```
    GET /stats
    ```

    **Specific agent:**
    ```
    GET /stats?agent_id=form_filler
    ```

    **Response:**
    ```json
    {
        "form_filler": {
            "total_invocations": 150,
            "successful_invocations": 145,
            "failed_invocations": 5,
            "last_invoked": "2025-01-13T10:30:00Z"
        }
    }
    ```
    """
    try:
        stats = agent_service.get_agent_stats(agent_id)
        return stats

    except Exception as e:
        logger.exception(f"Error getting agent stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

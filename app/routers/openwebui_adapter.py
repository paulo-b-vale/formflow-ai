# app/routers/openwebui_adapter.py
"""
OpenWebUI compatibility adapter
Maps Open WebUI's expected API format to our AI Form Assistant backend
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.services.enhanced_conversation_service import enhanced_conversation_service
from app.dependencies.auth import get_current_active_user
from app.schemas.user import UserResponse
import json
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)


# OpenWebUI-compatible models
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: List[Message]
    stream: bool = False
    session_id: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    role: str


async def get_user_token(request: Request) -> str:
    """Extract user token from request headers"""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return ""


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    user_token: str = Depends(get_user_token),
):
    """
    OpenWebUI-compatible chat completions endpoint
    Adapts OpenWebUI format to our enhanced_conversation service
    """
    try:
        # Extract the last user message from the conversation
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user message found in request"
            )

        last_user_message = user_messages[-1].content

        # Generate or use existing session_id
        session_id = request.session_id or f"session_{current_user.id}_{int(asyncio.get_event_loop().time())}"

        logger.info(f"Processing chat completion for user {current_user.id}, session: {session_id}")

        # Call our enhanced conversation service
        response_text = await enhanced_conversation_service.process_message(
            session_id=session_id,
            user_message=last_user_message,
            user_id=str(current_user.id),
            form_template_id=None,
            user_token=user_token,
            file_ids=None
        )

        # Format response in OpenWebUI-compatible format
        if request.stream:
            # TODO: Implement streaming response
            return StreamingResponse(
                stream_response(response_text, session_id),
                media_type="text/event-stream"
            )
        else:
            return {
                "id": f"chatcmpl-{session_id}",
                "object": "chat.completion",
                "created": int(asyncio.get_event_loop().time()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": len(last_user_message.split()),
                    "completion_tokens": len(response_text.split()),
                    "total_tokens": len(last_user_message.split()) + len(response_text.split())
                }
            }

    except Exception as e:
        logger.exception(f"Error in chat completions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )


async def stream_response(text: str, session_id: str):
    """Generate streaming response in OpenWebUI format"""
    # Split response into chunks for streaming effect
    words = text.split()
    for i, word in enumerate(words):
        chunk = {
            "id": f"chatcmpl-{session_id}",
            "object": "chat.completion.chunk",
            "created": int(asyncio.get_event_loop().time()),
            "model": "ai-form-assistant",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": word + " " if i < len(words) - 1 else word},
                    "finish_reason": None if i < len(words) - 1 else "stop"
                }
            ]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.05)  # Small delay for streaming effect

    yield "data: [DONE]\n\n"


@router.get("/models")
async def list_models(current_user: UserResponse = Depends(get_current_active_user)):
    """List available models (OpenWebUI compatibility)"""
    return {
        "data": [
            {
                "id": "ai-form-assistant",
                "object": "model",
                "created": 1677610602,
                "owned_by": "ai-form-assistant",
                "permission": [],
                "root": "ai-form-assistant",
                "parent": None,
            }
        ]
    }


@router.get("/users/me")
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Get current user info (OpenWebUI compatibility)"""
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "profile_image_url": None
    }
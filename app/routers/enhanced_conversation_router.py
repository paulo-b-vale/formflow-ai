# app/routers/enhanced_conversation_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.schemas.forms import ConversationRequest, ConversationResponse
from app.services.enhanced_conversation_service import enhanced_conversation_service
from app.dependencies.auth import get_current_active_user
from app.schemas.user import UserResponse
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

# --- DEBUGGING DEPENDENCY ---
async def log_request_body(request: Request):
    try:
        body = await request.json()
        logger.info(f"--- ENHANCED CONVERSATION REQUEST BODY ---")
        logger.info(json.dumps(body, indent=2))
        logger.info(f"--------------------------------------")
    except json.JSONDecodeError:
        logger.error("Could not parse request body as JSON.")
    except Exception as e:
        logger.error(f"Error reading request body: {e}")
    return True
# --- END DEBUGGING DEPENDENCY ---

async def get_user_token(request: Request) -> str:
    """Extract user token from request headers"""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return ""

@router.post(
    "/message",
    response_model=ConversationResponse,
    summary="Process a user message in an enhanced conversation",
    dependencies=[Depends(log_request_body)]
)
async def handle_message(
    request: ConversationRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    user_token: str = Depends(get_user_token),
    http_request: Request = None
):
    """
    Receives a user message, processes it through the enhanced conversation service,
    and returns the agent's response with enhanced token handling.
    """
    try:
        logger.info(f"📍 ROUTER: Received request: session_id={request.session_id}, user_message='{request.user_message}', form_id={request.form_id}")
        logger.info(f"📍 ROUTER: Current user ID: {current_user.id}")

        logger.info(f"📍 ROUTER: About to call service with session_id={request.session_id}")
        response_text = await enhanced_conversation_service.process_message(
            session_id=request.session_id,
            user_message=request.user_message,
            user_id=str(current_user.id),
            form_template_id=request.form_id,  # Pass optional form_id if provided
            user_token=user_token  # Pass the extracted token
        )
        logger.info(f"📍 ROUTER: Service returned, session_id should still be {request.session_id}")
        
        logger.info(f"Service returned response: '{response_text}'")
        
        response_obj = ConversationResponse(
            response=response_text,
            session_id=request.session_id
        )
        
        logger.info(f"Returning response object: {response_obj}")
        return response_obj
    except Exception as e:
        logger.exception(f"Error handling message in enhanced conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your message.",
        )
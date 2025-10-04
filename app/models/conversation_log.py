# app/models/conversation_log.py
from pydantic import Field
from typing import Optional
from .file import MongoBaseModel

class ConversationLog(MongoBaseModel):
    """Represents a single turn (a user message or a bot response) in a conversation."""
    session_id: str = Field(..., description="The unique ID for the conversation session.")
    form_response_id: Optional[str] = Field(None, description="The ID of the final saved form, linked after completion.")
    
    actor: str = Field(..., description="Indicates who sent the message ('user' or 'bot').")
    message: str = Field(..., description="The text content of the message.")
    
    state_at_turn: str = Field(..., description="The conversation state when this message was sent.")
from pydantic import BaseModel, Field
from typing import Optional


class ChatMessageRequest(BaseModel):
    """Request payload for chat endpoint."""

    session_id: Optional[str] = Field(
        None,
        description="Session ID. If not provided, a new session will be created."
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Message to send to the AI coach",
        examples=["Hi coach!", "How should I train today?", "I'm feeling tired"]
    )


class ChatMessageResponse(BaseModel):
    """Response from chat endpoint."""

    success: bool
    session_id: str
    message: str
    timestamp: str

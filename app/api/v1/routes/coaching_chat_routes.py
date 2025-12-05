from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.middlewares.clerk_auth import get_authenticated_user
from app.models.user import User
from app.api.v1.controllers.coaching_chat_controller import CoachingChatController
from app.schemas.coaching_chat_schemas import ChatMessageRequest, ChatMessageResponse
import os

router = APIRouter(prefix="/coaching/chat", tags=["AI Coaching Chat"])

IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "development") == "development"


@router.post(
    "",
    summary="Chat with AI Coach",
    description="Send a message to the AI coach. Creates session automatically if needed." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else ""),
    response_model=ChatMessageResponse
)
async def chat(
    payload: ChatMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authenticated_user)
):
    """
    Chat with the AI coach.

    Provide a message and optionally a session_id.
    If no session_id is provided, a new session will be created.
    """
    return await CoachingChatController.send_message(request, db, payload)


@router.post(
    "/stream",
    summary="Stream Chat with AI Coach"
)
async def chat_stream(
    payload: ChatMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authenticated_user)
):
    """Stream chat with AI coach using SSE."""
    from fastapi.responses import StreamingResponse
    
    return StreamingResponse(
        CoachingChatController.stream_message(request, db, payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

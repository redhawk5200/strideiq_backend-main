from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict
from datetime import datetime
import cuid

from app.models.coaching_session import CoachingSession
from app.schemas.coaching_chat_schemas import ChatMessageRequest
from app.utils.agent_instance import agent
from app.core.logger import get_logger

logger = get_logger("coaching_chat_controller")


class CoachingChatController:
    """Controller for AI coaching chat."""

    @staticmethod
    async def send_message(request: Request, db: AsyncSession, payload: ChatMessageRequest) -> Dict:
        """Send message to AI coach. Creates session if doesn't exist."""

        try:
            # auth
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user_id = request.state.user.id

            # data from payload
            session_id = payload.session_id
            message = payload.message

            # If no session_id, create new session
            if not session_id:
                session_id = cuid.cuid()
                session = CoachingSession(
                    id=session_id,
                    user_id=user_id
                )
                db.add(session)
                await db.commit()
                logger.info(f"🆕 Created new session {session_id} for user {user_id}")
            else:
                # Verify session exists
                result = await db.execute(
                    select(CoachingSession)
                    .where(CoachingSession.id == session_id)
                    .where(CoachingSession.user_id == user_id)
                )
                session = result.scalar_one_or_none()

                if not session:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Session not found"
                    )

                # Update last active
                session.last_active_at = datetime.utcnow()
                await db.commit()

            logger.info(f"💬 User {user_id}: {message[:50]}...")

            # Call agent with user_id in config
            agent_response = await agent.chat(
                message=message,
                thread_id=session_id,
                user_id=user_id
            )

            return {
                "success": True,
                "session_id": session_id,
                "message": agent_response.get("message"),
                "timestamp": datetime.utcnow().isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @staticmethod
    async def stream_message(request: Request, db: AsyncSession, payload: ChatMessageRequest):
        """Stream AI coach response with SSE."""
        import json
        from datetime import datetime
        
        try:
            # Auth check
            if not hasattr(request.state, 'user'):
                yield f"data: {json.dumps({'type': 'error', 'message': 'Not authenticated'})}\n\n"
                return
            
            user_id = request.state.user.id
            session_id = payload.session_id
            message = payload.message
            
            # Create or verify session
            if not session_id:
                session_id = cuid.cuid()
                session = CoachingSession(id=session_id, user_id=user_id)
                db.add(session)
                await db.commit()
                logger.info(f"🆕 Created session {session_id}")
            else:
                result = await db.execute(
                    select(CoachingSession)
                    .where(CoachingSession.id == session_id)
                    .where(CoachingSession.user_id == user_id)
                )
                session = result.scalar_one_or_none()
                if not session:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
                    return
                session.last_active_at = datetime.utcnow()
                await db.commit()
            
            logger.info(f"💬 Streaming for user {user_id}: {message[:50]}...")
            
            # Stream from agent
            async for event in agent.agent.astream_events(
                {"messages": [{"role": "user", "content": f"[Today's date: {datetime.now().strftime('%Y-%m-%d')}]\n\n{message}"}]},
                config={"configurable": {"thread_id": session_id, "user_id": user_id}},
                version="v2"
            ):
                event_type = event.get("event")
                data = event.get("data", {})
                name = event.get("name", "")
                
                # Token streaming
                if event_type in ("on_chat_model_stream", "on_llm_stream"):
                    chunk = data.get("chunk")
                    token = ""
                    if hasattr(chunk, "content"):
                        token = chunk.content or ""
                    if token:
                        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                
                # Tool events
                elif event_type == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': name})}\n\n"
                
                elif event_type == "on_tool_end":
                    output = str(data.get("output", ""))[:200]  # Limit output size
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': name, 'output': output})}\n\n"
            
            # Done event
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

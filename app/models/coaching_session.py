from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class CoachingSession(Base):
    """
    Stores coaching chat sessions. Conversation history is managed in-memory by LangGraph.
    This table only tracks session metadata.
    """
    __tablename__ = "coaching_sessions"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)

    # Session tracking
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="coaching_sessions")

    __table_args__ = (
        Index("ix_coaching_session_user_started", "user_id", "started_at"),
    )

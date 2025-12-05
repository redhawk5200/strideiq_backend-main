from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
from app.enums import MoodType
import cuid


class UserMood(Base):
    """User's mood tracking over time."""

    __tablename__ = "user_moods"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    profile_id = Column(String(25), ForeignKey("user_profiles.id"), nullable=False, index=True)

    mood_type = Column(SQLEnum(MoodType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    notes = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profile = relationship("UserProfile", back_populates="moods")

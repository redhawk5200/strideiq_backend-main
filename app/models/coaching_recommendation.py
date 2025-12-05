from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid
import enum


class RecommendationStatus(str, enum.Enum):
    """Status of a coaching recommendation."""
    PENDING = "pending"           # Recommendation given, waiting for user action
    COMPLETED = "completed"       # User completed the recommended workout
    SKIPPED = "skipped"          # User didn't do the workout
    PARTIAL = "partial"          # User did something different but close


class CoachingRecommendation(Base):
    """
    Stores AI coaching recommendations to track what was suggested
    and whether the user followed through.
    """
    __tablename__ = "coaching_recommendations"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)

    # When this recommendation was given
    recommendation_date = Column(DateTime, nullable=False, index=True)

    # What was recommended
    workout_type = Column(String(50), nullable=True)  # "run", "walk", "rest", "cycling", etc.
    duration_minutes = Column(Integer, nullable=True)  # Recommended duration
    intensity_zone = Column(String(20), nullable=True)  # "zone_1", "zone_2", etc.
    heart_rate_range = Column(String(20), nullable=True)  # "140-150" bpm range

    # Full recommendation text (all sections)
    todays_training = Column(Text, nullable=True)
    nutrition_fueling = Column(Text, nullable=True)
    recovery_protocol = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)

    # Compliance tracking (using String to avoid enum migration issues)
    status = Column(String(20), default="pending", nullable=False)
    actual_workout_id = Column(String(25), ForeignKey("workout_sessions.id"), nullable=True)  # If completed
    compliance_notes = Column(Text, nullable=True)  # "User did 20 min instead of 30 min"

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="coaching_recommendations")
    actual_workout = relationship("WorkoutSession", foreign_keys=[actual_workout_id])

    __table_args__ = (
        Index("ix_coaching_rec_user_date", "user_id", "recommendation_date"),
        Index("ix_coaching_rec_user_status", "user_id", "status"),
    )

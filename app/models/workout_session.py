from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Float, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class WorkoutSession(Base):
    """
    Exercise/workout sessions from fitness trackers.
    Stores details about physical activities tracked by devices.
    """
    __tablename__ = "workout_sessions"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(25), ForeignKey("devices.id"), nullable=True)
    provider = Column(String(40), nullable=False)
    source_record_id = Column(String(128), nullable=True)
    ingest_batch_id = Column(String(25), ForeignKey("health_ingest_batches.id"), nullable=True)

    # Workout details
    activity_type = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)  # UTC
    end_time = Column(DateTime, nullable=False)  # UTC
    duration_seconds = Column(Integer, nullable=False)

    # Metrics (optional)
    calories = Column(Float, nullable=True)
    distance_miles = Column(Float, nullable=True)
    avg_heart_rate = Column(Integer, nullable=True)
    max_heart_rate = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="workout_sessions")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "source_record_id", name="uq_workout_external"),
        Index("ix_workout_user_time", "user_id", "start_time"),
    )

from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
from app.enums import TrainingLevel, TimeWindow, WorkoutType
import cuid


class TrainingPreferences(Base):
    """User training preferences and schedule."""
    
    __tablename__ = "training_preferences"
    
    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    profile_id = Column(String(25), ForeignKey("user_profiles.id"), nullable=False, unique=True, index=True)
    
    training_level = Column(SQLEnum(TrainingLevel), nullable=False)
    sessions_per_day = Column(Integer, default=1)
    days_per_week = Column(Integer, default=3)
    preferred_time_window = Column(SQLEnum(TimeWindow), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="training_preferences")


class UserWorkoutPreference(Base):
    """User's preferred workout types."""
    
    __tablename__ = "user_workout_preferences"
    
    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    profile_id = Column(String(25), ForeignKey("user_profiles.id"), nullable=False, index=True)
    
    workout_type = Column(SQLEnum(WorkoutType), nullable=False)
    rank = Column(Integer, nullable=True)  # For ordering preferences
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="workout_preferences")
    
    __table_args__ = (
        UniqueConstraint("profile_id", "workout_type", name="uq_profile_workout_type"),
    )

from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class User(Base):
    """User model for authentication and user management."""
    
    __tablename__ = "users"
    
    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    email = Column(String(255), unique=True, index=True, nullable=False)
    clerk_id = Column(String(255), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    type = Column(String(50), nullable=False)  # admin, user only
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Health-related relationships
    devices = relationship("Device", back_populates="user")
    hr_samples = relationship("HeartRateSample", back_populates="user")
    step_minutes = relationship("StepMinute", back_populates="user")
    sleep_sessions = relationship("SleepSession", back_populates="user")
    vo2_estimates = relationship("VO2MaxEstimate", back_populates="user")
    workout_sessions = relationship("WorkoutSession", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    consents = relationship("UserConsent", back_populates="user", cascade="all, delete-orphan")
    weight_measurements = relationship("BodyWeightMeasurement", back_populates="user", cascade="all, delete-orphan")
    coaching_recommendations = relationship("CoachingRecommendation", back_populates="user", cascade="all, delete-orphan")
    injuries = relationship("UserInjury", back_populates="user", cascade="all, delete-orphan")

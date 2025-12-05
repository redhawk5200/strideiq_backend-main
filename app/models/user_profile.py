from sqlalchemy import Column, String, ForeignKey, DateTime, Date, Float, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class UserProfile(Base):
    """Extended user profile for fitness and health data."""
    
    __tablename__ = "user_profiles"
    
    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Personal Information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)  # 'male', 'female', 'other', 'prefer_not_to_say'
    
    # Demographics (supplement Clerk data)
    birth_date = Column(Date, nullable=True)
    height_inches = Column(Float, nullable=True)
    unit_preference = Column(String(10), default="imperial")  # Only imperial units supported
    
    # Calculated field - computed from birth_date
    age = Column(Integer, nullable=True)  
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    goals = relationship("UserGoal", back_populates="profile", cascade="all, delete-orphan")
    training_preferences = relationship("TrainingPreferences", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    workout_preferences = relationship("UserWorkoutPreference", back_populates="profile", cascade="all, delete-orphan")
    onboarding_progress = relationship("OnboardingProgress", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    moods = relationship("UserMood", back_populates="profile", cascade="all, delete-orphan")
    daily_training_intentions = relationship("UserDailyTrainingIntention", back_populates="profile", cascade="all, delete-orphan")

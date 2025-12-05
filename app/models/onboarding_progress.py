from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
from app.enums import OnboardingStep
import cuid


class OnboardingProgress(Base):
    """Track user onboarding progress."""

    __tablename__ = "onboarding_progress"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    profile_id = Column(String(25), ForeignKey("user_profiles.id"), nullable=False, unique=True, index=True)

    current_step = Column(SQLEnum(OnboardingStep), default=OnboardingStep.BASIC_INFO)
    completed_steps = Column(Text, default="")  # JSON array of completed steps

    # Store the exact frontend step number (1-13) for precise resume
    current_frontend_step = Column(String(100), nullable=True)  # Store screen name or step number

    is_completed = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("UserProfile", back_populates="onboarding_progress")

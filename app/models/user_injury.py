"""
User Injury Model

Tracks injuries and pain reported by users, their recovery progress,
and activity restrictions.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Text, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid
import enum


class InjuryStatus(str, enum.Enum):
    """Status of an injury."""
    ACTIVE = "active"           # Currently injured
    RECOVERING = "recovering"   # Getting better but still affecting training
    RECOVERED = "recovered"     # Fully healed
    CHRONIC = "chronic"         # Long-term ongoing issue


class SeverityLevel(str, enum.Enum):
    """Severity level of an injury."""
    MILD = "mild"         # Minor discomfort, can train with modifications
    MODERATE = "moderate" # Significant pain, requires rest or major modifications
    SEVERE = "severe"     # Serious injury, may need medical attention


class ImprovementLevel(str, enum.Enum):
    """How injury is progressing."""
    IMPROVING = "improving"  # Getting better
    SAME = "same"           # No change
    WORSE = "worse"         # Getting worse


class UserInjury(Base):
    """
    Stores user injuries, pain, and recovery tracking.
    """
    __tablename__ = "user_injuries"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)

    # Injury Details
    injury_type = Column(String(100), nullable=False)  # "shin_splints", "runners_knee", etc.
    affected_area = Column(String(100), nullable=False)  # "left_knee", "right_ankle", etc.
    severity_level = Column(String(20), nullable=False)  # "mild", "moderate", "severe"

    # Pain Tracking (1-10 scale)
    initial_pain_level = Column(Integer, nullable=True)  # Pain level when first reported
    current_pain_level = Column(Integer, nullable=True)  # Current pain level (updated)

    # Timeline
    injury_date = Column(DateTime, nullable=False, index=True)  # When injury occurred
    reported_date = Column(DateTime, nullable=False)  # When user reported it
    expected_recovery_date = Column(DateTime, nullable=True)  # Estimated recovery
    actual_recovery_date = Column(DateTime, nullable=True)  # When it actually recovered

    # Status
    status = Column(String(20), default="active", nullable=False, index=True)

    # Description and Symptoms
    description = Column(Text, nullable=True)  # Detailed description from user
    symptoms = Column(Text, nullable=True)  # pain during running, swelling, etc.
    treatment_plan = Column(Text, nullable=True)  # rest, ice, PT, etc.

    # Activity Restrictions
    activity_restrictions = Column(JSON, nullable=True)  # {"no_running": true, "max_distance_miles": 2}

    # Tracking Notes
    recovery_notes = Column(Text, nullable=True)  # Coach's notes on progress
    last_update_date = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="injuries")
    updates = relationship("InjuryUpdate", back_populates="injury", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_user_injuries_status_user', 'user_id', 'status'),
        Index('idx_user_injuries_date', 'injury_date'),
    )

    def __repr__(self):
        return f"<UserInjury {self.injury_type} - {self.affected_area} ({self.status})>"

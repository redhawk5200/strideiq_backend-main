from sqlalchemy import Column, String, ForeignKey, DateTime, Float, Boolean, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
from app.enums import GoalType, GoalPriority, ConsentType
import cuid


class UserConsent(Base):
    """User consent tracking for privacy compliance."""
    
    __tablename__ = "user_consents"
    
    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    
    consent_type = Column(SQLEnum(ConsentType), nullable=False)
    granted = Column(Boolean, nullable=False)
    granted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="consents")
    
    __table_args__ = (
        UniqueConstraint("user_id", "consent_type", name="uq_user_consent"),
    )


# Reuse table args tuple definition for UserGoal indexes

class UserGoal(Base):
    """User fitness goals and targets."""
    
    __tablename__ = "user_goals"
    
    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    profile_id = Column(String(25), ForeignKey("user_profiles.id"), nullable=False, index=True)
    
    goal_type = Column(String(20), nullable=False)  # Store as string to avoid enum issues
    description = Column(String(500), nullable=True)  # Goal description
    target_value = Column(String(50), nullable=True)  # Target value as string (flexible for different goal types)
    unit = Column(String(10), nullable=True)     # "kg", "lbs", "steps", "min"
    target_date = Column(DateTime, nullable=True)
    priority = Column(String(10), default="medium")  # Store as string to avoid enum issues
    
    active = Column(Boolean, default=True)
    achieved = Column(Boolean, default=False)
    achieved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="goals")

    __table_args__ = (
        Index("ix_user_goals_profile_active", "profile_id", "active"),
        Index("ix_user_goals_profile_achieved", "profile_id", "achieved"),
    )


class BodyWeightMeasurement(Base):
    """Body weight tracking over time."""
    
    __tablename__ = "body_weight_measurements"
    
    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    
    value_lbs = Column(Float, nullable=False)
    measured_at = Column(DateTime, nullable=False, index=True)
    source = Column(String(20), default="manual")  # "manual", "healthkit", "fitbit", etc.
    notes = Column(String(500), nullable=True)  # Optional notes about the measurement
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="weight_measurements")

    __table_args__ = (
        UniqueConstraint("user_id", "measured_at", name="uq_weight_user_timestamp"),
    )

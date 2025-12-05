"""
Injury Update Model

Tracks progress updates for injuries over time.
Creates a timeline of recovery showing how injury improves or worsens.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Text, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class InjuryUpdate(Base):
    """
    Stores timeline of injury progress updates.
    Each update represents a check-in about how the injury is feeling.
    """
    __tablename__ = "injury_updates"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    injury_id = Column(String(25), ForeignKey("user_injuries.id"), nullable=False, index=True)
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)

    # Update Details
    update_date = Column(DateTime, nullable=False, index=True)  # When this update was made
    pain_level = Column(Integer, nullable=True)  # Pain level at time of update (1-10)
    status = Column(String(20), nullable=True)  # Status at time of update

    # Progress Notes
    notes = Column(Text, nullable=True)  # "Feeling better today", "Pain increased after run"
    improvement_level = Column(String(20), nullable=True)  # "improving", "same", "worse"

    # Activities Since Last Update
    activities_performed = Column(JSON, nullable=True)  # What they did since last check-in
    pain_triggers = Column(JSON, nullable=True)  # What activities caused pain

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    injury = relationship("UserInjury", back_populates="updates")
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index('idx_injury_updates_injury_date', 'injury_id', 'update_date'),
    )

    def __repr__(self):
        return f"<InjuryUpdate {self.injury_id} - Pain: {self.pain_level}/10 ({self.improvement_level})>"

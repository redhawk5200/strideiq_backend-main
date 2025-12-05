from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class StepMinute(Base):
    """
    Per-minute step counts.
    """
    __tablename__ = "step_minute"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(25), ForeignKey("devices.id"), nullable=True)
    provider = Column(String(40), nullable=False)
    source_record_id = Column(String(128), nullable=True)
    ingest_batch_id = Column(String(25), ForeignKey("health_ingest_batches.id"), nullable=True)

    start_minute = Column(DateTime, nullable=False, index=True)  # inclusive, UTC
    steps = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="step_minutes")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "start_minute", name="uq_steps_min"),
        Index("ix_steps_user_minute", "user_id", "start_minute"),
    )

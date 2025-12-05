from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class SleepSession(Base):
    """
    Sleep sessions with optional per-epoch stages.
    Durations in seconds; stages: 'awake'|'light'|'deep'|'rem'
    """
    __tablename__ = "sleep_sessions"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(40), nullable=False)
    source_record_id = Column(String(128), nullable=True)
    ingest_batch_id = Column(String(25), ForeignKey("health_ingest_batches.id"), nullable=True)

    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    duration_s = Column(Integer, nullable=False)

    score = Column(Integer, nullable=True)          # 0–100 if the provider supplies
    latency_s = Column(Integer, nullable=True)
    awakenings = Column(Integer, nullable=True)
    efficiency_pct = Column(Integer, nullable=True)

    metrics = Column(JSON, nullable=True)  # {"avg_hr": 54, "resp_rate": 13}
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="sleep_sessions")
    epochs = relationship("SleepEpoch", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "source_record_id", name="uq_sleep_external"),
        Index("ix_sleep_user_start", "user_id", "start_time"),
    )


class SleepEpoch(Base):
    """Sleep epoch data for detailed sleep stage tracking."""
    
    __tablename__ = "sleep_epochs"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    session_id = Column(String(25), ForeignKey("sleep_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    stage = Column(String(16), nullable=False)  # 'awake'|'light'|'deep'|'rem'

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("SleepSession", back_populates="epochs")

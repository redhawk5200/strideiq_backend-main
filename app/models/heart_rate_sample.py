from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Float, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class HeartRateSample(Base):
    """
    Continuous or minute-level HR samples.
    Units: bpm
    """
    __tablename__ = "heart_rate_samples"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(25), ForeignKey("devices.id"), nullable=True)
    provider = Column(String(40), nullable=False)
    source_record_id = Column(String(128), nullable=True)  # provider row id
    ingest_batch_id = Column(String(25), ForeignKey("health_ingest_batches.id"), nullable=True)

    captured_at = Column(DateTime, nullable=False, index=True)  # UTC
    bpm = Column(Integer, nullable=False)

    context = Column(String(24), nullable=True)  # 'resting'|'workout'|'sleep'|'unknown'
    confidence = Column(Float, nullable=True)
    quality = Column(String(24), nullable=True)  # 'good'|'questionable'|'bad'
    flags = Column(JSON, nullable=True)         # e.g., {"sensor_lock_on_delay": true}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="hr_samples")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "source_record_id", name="uq_hr_external"),
        Index("ix_hr_user_time", "user_id", "captured_at"),
    )

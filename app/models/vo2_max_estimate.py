from sqlalchemy import Column, String, ForeignKey, DateTime, Float, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class VO2MaxEstimate(Base):
    """
    VO2max estimates.
    Units: mL·kg⁻¹·min⁻¹
    """
    __tablename__ = "vo2max_estimates"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(25), ForeignKey("devices.id"), nullable=True)
    provider = Column(String(40), nullable=False)
    source_record_id = Column(String(128), nullable=True)
    ingest_batch_id = Column(String(25), ForeignKey("health_ingest_batches.id"), nullable=True)

    measured_at = Column(DateTime, nullable=False, index=True)
    ml_per_kg_min = Column(Float, nullable=False)          # 10–90 typically
    estimation_method = Column(String(40), nullable=False) # 'apple_health'|'fitbit_cardio_fitness'|'lab'|'field_test'
    context = Column(String(32), nullable=True)            # 'running'|'walking'|...

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="vo2_estimates")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "source_record_id", name="uq_vo2_external"),
        Index("ix_vo2_user_time", "user_id", "measured_at"),
    )

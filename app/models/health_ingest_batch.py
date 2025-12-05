from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Text, Index
from datetime import datetime
from app.database.base import Base
import cuid


class HealthIngestBatch(Base):
    """
    Logical batch to tag incoming rows from a single sync/stream.
    """
    __tablename__ = "health_ingest_batches"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(40), nullable=False)
    device_id = Column(String(25), ForeignKey("devices.id"), nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    count_received = Column(Integer, default=0)
    count_stored = Column(Integer, default=0)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_ingest_user_provider", "user_id", "provider"),
    )

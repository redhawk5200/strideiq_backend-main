from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, Index
from datetime import datetime
from app.database.base import Base
import cuid


class WebhookEvent(Base):
    """
    Stores provider webhook payloads for auditing/reprocessing.
    """
    __tablename__ = "webhook_events"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    provider = Column(String(40), nullable=False)  # 'fitbit' | 'garmin' | etc.
    event_type = Column(String(80), nullable=True)
    payload = Column(JSON, nullable=True)
    headers = Column(JSON, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_webhook_provider_time", "provider", "received_at"),
        Index("ix_webhook_processed_time", "processed", "received_at"),
    )

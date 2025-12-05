from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint, Index
from datetime import datetime
from app.database.base import Base
import cuid


class IdempotencyKey(Base):
    """
    Prevent duplicate processing of bulk ingests (e.g., mobile retry or webhook replay).
    """
    __tablename__ = "idempotency_keys"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    endpoint = Column(String(128), nullable=False)
    key_hash = Column(String(64), nullable=False)  # sha256 of client key
    status = Column(String(24), nullable=False, default="accepted")  # accepted|completed|failed
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", "key_hash", name="uq_idem_user_endpoint_key"),
        Index("ix_idem_user_endpoint", "user_id", "endpoint"),
    )

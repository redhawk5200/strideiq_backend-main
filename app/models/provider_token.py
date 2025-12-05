from sqlalchemy import Column, String, ForeignKey, DateTime, LargeBinary, UniqueConstraint, Index
from datetime import datetime
from app.database.base import Base
import cuid


class ProviderToken(Base):
    """
    Encrypted OAuth tokens for Fitbit/Google (Health Connect) and others.
    """
    __tablename__ = "provider_tokens"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(40), nullable=False)  # 'fitbit' | 'health_connect' | 'garmin' (future)
    access_token_encrypted = Column(LargeBinary, nullable=False)
    refresh_token_encrypted = Column(LargeBinary, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    scope = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_provider_token_user_provider"),
        Index("ix_provider_token_user_provider", "user_id", "provider"),
    )

from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class Device(Base):
    """
    A physical or virtual source of health data (Apple Watch via HealthKit, Fitbit, Health Connect, BLE)
    """
    __tablename__ = "devices"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    user_id = Column(String(25), ForeignKey("users.id"), nullable=False, index=True)

    provider = Column(String(40), nullable=False)           # 'apple_healthkit' | 'fitbit' | 'health_connect' | 'ble'
    external_device_id = Column(String(128), nullable=True) # provider device id if available
    make = Column(String(80), nullable=True)                # Apple, Fitbit, Samsung, Polar
    model = Column(String(80), nullable=True)               # Series 9, Versa 4, etc.
    firmware = Column(String(80), nullable=True)
    name = Column(String(128), nullable=True)
    last_sync_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="devices")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "external_device_id", name="uq_device_user_provider_external"),
        Index("ix_device_user_provider", "user_id", "provider"),
    )

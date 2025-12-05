from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database.base import Base
from app.enums import DailyTrainingIntention
import cuid


class UserDailyTrainingIntention(Base):
    """User's daily training intention (Yes/No/Maybe for training today)."""

    __tablename__ = "user_daily_training_intentions"

    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    profile_id = Column(String(25), ForeignKey("user_profiles.id"), nullable=False, index=True)

    intention = Column(SQLEnum(DailyTrainingIntention, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    intention_date = Column(Date, default=date.today, nullable=False, index=True)
    notes = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("UserProfile", back_populates="daily_training_intentions")

    __table_args__ = (
        UniqueConstraint("profile_id", "intention_date", name="uq_training_intention_profile_date"),
    )

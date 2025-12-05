from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import cuid


class UserMedicalCondition(Base):
    """Junction table linking users to their medical conditions."""
    
    __tablename__ = "user_medical_conditions"
    
    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    profile_id = Column(String(25), ForeignKey("user_profiles.id"), nullable=False, index=True)
    medical_condition_id = Column(String(25), ForeignKey("medical_conditions.id"), nullable=False, index=True)
    notes = Column(String(500), nullable=True)  # Optional notes about the condition
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile = relationship("UserProfile", backref="medical_conditions")
    condition = relationship("MedicalCondition")
    
    def __repr__(self):
        return f"<UserMedicalCondition(profile_id='{self.profile_id}', condition_id='{self.medical_condition_id}')>"

    __table_args__ = (
        UniqueConstraint("profile_id", "medical_condition_id", name="uq_medical_condition_profile"),
    )

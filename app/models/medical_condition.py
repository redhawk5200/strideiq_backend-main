from sqlalchemy import Column, String, Boolean, Integer
from datetime import datetime
from app.database.base import Base
import cuid


class MedicalCondition(Base):
    """Reference table for available medical conditions."""
    
    __tablename__ = "medical_conditions"
    
    id = Column(String(25), primary_key=True, index=True, default=lambda: cuid.cuid())
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)  # e.g., 'cardiovascular', 'respiratory', 'musculoskeletal'
    display_order = Column(Integer, default=0)  # For ordering on frontend
    is_active = Column(Boolean, default=True)  # To enable/disable without deleting
    
    def __repr__(self):
        return f"<MedicalCondition(name='{self.name}')>"

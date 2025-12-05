from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional

from app.database.connection import get_db  # Fixed import
from app.models.user import User  # Fixed import
from app.middlewares.clerk_auth import get_authenticated_user
from app.core.logger import get_logger

logger = get_logger("user_routes")
router = APIRouter()

@router.get("/user/me", tags=["User"])
async def get_current_user(
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user's information"""
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "clerk_id": current_user.clerk_id,
        "type": current_user.type,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }
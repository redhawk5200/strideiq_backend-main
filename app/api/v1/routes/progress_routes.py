"""
Progress Routes
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.middlewares.clerk_auth import get_authenticated_user
from app.models.user import User
from app.api.v1.controllers.progress_controller import ProgressController
from app.schemas.progress_schemas import ProgressResponse
import os

router = APIRouter(prefix="/progress", tags=["Progress"])

IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "development") == "development"


@router.get(
    "",
    summary="Get User Progress",
    description="Get comprehensive progress data including weekly stats, VO2 trends, recent workouts, and injuries." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else ""),
    response_model=ProgressResponse
)
async def get_progress(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authenticated_user)
):
    """
    Get comprehensive progress data for the authenticated user.

    Returns:
    - Current week stats (last 7 days)
    - Last 4 weeks comparison
    - VO2 max trend (last 30 days)
    - Recent workouts (last 7 days)
    - Active injuries
    - Personal records (longest run, best VO2, total workouts)
    - Current workout streak
    """
    return await ProgressController.get_progress(request, db)

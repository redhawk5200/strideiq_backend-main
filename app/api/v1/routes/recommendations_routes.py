from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.middlewares.clerk_auth import get_authenticated_user
from app.models.user import User
from app.api.v1.controllers.recommendations_controller import RecommendationsController
from app.schemas.recommendation_schemas import UpdatePlanStatusRequest, UpdatePlanStatusResponse
import os

router = APIRouter(prefix="/recommendations", tags=["AI Coaching Recommendations"])

# Development mode detection
IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "development") == "development"


@router.get(
    "/generate",
    summary="Generate AI Coaching Recommendations",
    description="Generate comprehensive AI-powered coaching recommendations based on user demographics, goals, and health data." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def generate_recommendations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """
    Generate comprehensive AI coaching recommendations.

    This endpoint provides:
    - Overall fitness assessment
    - Personalized training recommendations
    - Nutrition and recovery guidance
    - Progress targets and goals
    - Quick action items

    Requires:
    - Authentication
    - User profile (recommended but not required)

    The AI analyzes:
    - Demographics (age, gender, height)
    - Goals (VO₂max, race time, weight)
    - Training preferences
    - Weight history
    - VO₂max data
    - Heart rate patterns
    - Sleep quality
    """
    return await RecommendationsController.generate_recommendations(request, db)


@router.get(
    "/stream",
    summary="Stream AI Coaching Recommendations",
    description="Stream AI-powered coaching recommendations in real-time using Server-Sent Events." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def stream_recommendations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """
    Stream comprehensive AI coaching recommendations in real-time.

    This endpoint uses Server-Sent Events (SSE) to stream recommendations as they are generated.

    Event types:
    - status: Progress updates
    - context: User context summary
    - chunk: AI response chunks
    - complete: Final recommendations
    - error: Error messages

    Requires:
    - Authentication
    - User profile (recommended but not required)
    """
    return await RecommendationsController.stream_recommendations(request, db)


@router.get(
    "/quick-actions",
    summary="Get Quick Actions",
    description="Get quick action items and recommendations for immediate next steps." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def get_quick_actions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """
    Get quick action items based on user data.

    Returns prioritized action items such as:
    - Missing data to complete
    - Goal progress tracking
    - Workout scheduling
    - Device connection reminders

    Requires:
    - Authentication
    """
    return await RecommendationsController.get_quick_actions(request, db)


@router.get(
    "/summary",
    summary="Get Data Summary",
    description="Get a summary of available user data for recommendations." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def get_recommendations_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """
    Get a summary of available user data.

    Returns information about:
    - Profile completeness
    - Available health metrics
    - Goals configured
    - Training preferences set

    Useful for determining data quality before generating full recommendations.

    Requires:
    - Authentication
    """
    return await RecommendationsController.get_recommendations_summary(request, db)


@router.get(
    "/latest",
    summary="Get Latest Recommendation",
    description="Get the most recent coaching recommendation for the authenticated user." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def get_latest_recommendation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """
    Get the latest coaching recommendation.

    Returns the most recent recommendation including:
    - Training plan for the day
    - Nutrition and fueling guidelines
    - Recovery protocol
    - Reasoning behind the recommendation
    - Compliance status (pending/completed/skipped)

    Useful for displaying the current recommendation on the frontend.

    Requires:
    - Authentication
    """
    return await RecommendationsController.get_latest_recommendation(request, db)


@router.patch(
    "/{recommendation_id}/status",
    summary="Update Plan Status",
    description="Update the status of a coaching recommendation (completed/skipped/partial)." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else ""),
    response_model=UpdatePlanStatusResponse
)
async def update_plan_status(
    recommendation_id: str,
    payload: UpdatePlanStatusRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authenticated_user)
):
    """
    Update the status of a coaching recommendation.

    Allows users to mark their daily coaching plan as:
    - **completed**: User completed the workout as recommended
    - **skipped**: User did not do the workout
    - **partial**: User did something different or only completed part of it

    You can also provide optional notes to explain the status update.

    Requires:
    - Authentication
    - Valid recommendation ID that belongs to the authenticated user
    """
    return await RecommendationsController.update_plan_status(request, db, recommendation_id, payload)


@router.get(
    "/health",
    summary="Health Check",
    description="Simple health check for recommendations service. No authentication required."
)
async def recommendations_health():
    """Health check for recommendations endpoints."""
    return {
        "status": "healthy",
        "service": "recommendations",
        "development_mode": IS_DEVELOPMENT,
        "message": "AI Recommendations service is running"
    }

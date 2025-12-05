from fastapi import HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import Dict

from app.services.coaching_recommendations_service import CoachingRecommendationsService
from app.models.coaching_recommendation import CoachingRecommendation
from app.schemas.recommendation_schemas import UpdatePlanStatusRequest, UpdatePlanStatusResponse
from app.core.logger import get_logger
from datetime import datetime

logger = get_logger("recommendations_controller")


class RecommendationsController:
    """Controller for AI coaching recommendations."""

    @staticmethod
    async def generate_recommendations(
        request: Request,
        db: AsyncSession
    ) -> Dict:
        """Generate comprehensive AI coaching recommendations for the authenticated user."""

        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user

            # Initialize service
            recommendations_service = CoachingRecommendationsService()

            # Generate recommendations
            result = await recommendations_service.generate_comprehensive_recommendations(
                db, user.id
            )

            if not result.get("success"):
                logger.warning(f"Failed to generate recommendations for user {user.id}: {result.get('error')}")
                # Return fallback recommendations instead of error
                return {
                    "status": "partial_success",
                    "message": "Generated basic recommendations with limited data",
                    "user_id": user.id,
                    **result
                }

            logger.info(f"Generated recommendations for user {user.email}")
            return {
                "status": "success",
                **result
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate recommendations"
            )

    @staticmethod
    async def stream_recommendations(
        request: Request,
        db: AsyncSession
    ) -> StreamingResponse:
        """Stream AI coaching recommendations in real-time."""

        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user

            # Initialize service
            recommendations_service = CoachingRecommendationsService()

            # Return streaming response
            return StreamingResponse(
                recommendations_service.stream_recommendations(db, user.id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error streaming recommendations: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stream recommendations"
            )

    @staticmethod
    async def get_quick_actions(
        request: Request,
        db: AsyncSession
    ) -> Dict:
        """Get quick action items for the user."""

        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user

            # Initialize service
            recommendations_service = CoachingRecommendationsService()

            # Gather context
            context = await recommendations_service._gather_user_context(db, user.id)

            # Generate quick actions
            quick_actions = recommendations_service._generate_quick_actions(context)

            return {
                "status": "success",
                "user_id": user.id,
                "quick_actions": quick_actions,
                "count": len(quick_actions)
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting quick actions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get quick actions"
            )

    @staticmethod
    async def get_recommendations_summary(
        request: Request,
        db: AsyncSession
    ) -> Dict:
        """Get a brief summary of available data for recommendations."""

        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user

            # Initialize service
            recommendations_service = CoachingRecommendationsService()

            # Gather context
            context = await recommendations_service._gather_user_context(db, user.id)

            # Create summary
            summary = recommendations_service._create_context_summary(context)

            return {
                "status": "success",
                "user_id": user.id,
                "data_summary": summary
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting recommendations summary: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get recommendations summary"
            )

    @staticmethod
    async def get_latest_recommendation(
        request: Request,
        db: AsyncSession
    ) -> Dict:
        """Get the latest coaching recommendation for the authenticated user."""

        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user

            # Get latest recommendation
            result = await db.execute(
                select(CoachingRecommendation)
                .where(CoachingRecommendation.user_id == user.id)
                .order_by(desc(CoachingRecommendation.recommendation_date))
                .limit(1)
            )
            latest_recommendation = result.scalar_one_or_none()

            if not latest_recommendation:
                return {
                    "status": "success",
                    "message": "No recommendations found",
                    "recommendation": None
                }

            # Format the recommendation
            recommendation_data = {
                "id": latest_recommendation.id,
                "recommendation_date": latest_recommendation.recommendation_date.isoformat(),
                "workout_type": latest_recommendation.workout_type,
                "duration_minutes": latest_recommendation.duration_minutes,
                "intensity_zone": latest_recommendation.intensity_zone,
                "heart_rate_range": latest_recommendation.heart_rate_range,
                "todays_training": latest_recommendation.todays_training,
                "nutrition_fueling": latest_recommendation.nutrition_fueling,
                "recovery_protocol": latest_recommendation.recovery_protocol,
                "reasoning": latest_recommendation.reasoning,
                "status": latest_recommendation.status,
                "compliance_notes": latest_recommendation.compliance_notes,
                "created_at": latest_recommendation.created_at.isoformat()
            }

            logger.info(f"Retrieved latest recommendation for user {user.email}")
            return {
                "status": "success",
                "user_id": user.id,
                "recommendation": recommendation_data
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting latest recommendation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get latest recommendation"
            )

    @staticmethod
    async def update_plan_status(
        request: Request,
        db: AsyncSession,
        recommendation_id: str,
        payload: UpdatePlanStatusRequest
    ) -> Dict:
        """Update the status of a coaching recommendation (completed/skipped/partial)."""

        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user

            # Get the recommendation
            result = await db.execute(
                select(CoachingRecommendation)
                .where(CoachingRecommendation.id == recommendation_id)
                .where(CoachingRecommendation.user_id == user.id)
            )
            recommendation = result.scalar_one_or_none()

            if not recommendation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Recommendation {recommendation_id} not found or does not belong to user"
                )

            # Update status
            old_status = recommendation.status
            recommendation.status = payload.status.value
            recommendation.updated_at = datetime.utcnow()

            # Update compliance notes if provided
            if payload.notes:
                recommendation.compliance_notes = payload.notes

            await db.commit()

            logger.info(
                f"Updated recommendation {recommendation_id} status: "
                f"{old_status} -> {payload.status.value} for user {user.email}"
            )

            return UpdatePlanStatusResponse(
                success=True,
                message=f"Plan status updated to {payload.status.value}",
                recommendation_id=recommendation_id,
                new_status=payload.status.value
            ).dict()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating plan status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update plan status"
            )

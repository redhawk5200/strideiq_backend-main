"""
Update Plan Tool

Allows AI to update existing coaching plans in the database
"""

from typing import Dict, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.future import select

from app.models.coaching_recommendation import CoachingRecommendation
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("update_plan_tool")


class UpdatePlanInput(BaseModel):
    """Input schema for updating a coaching plan."""
    plan_id: str = Field(
        description="ID of the plan to update"
    )
    todays_training: Optional[str] = Field(
        default=None,
        description="Modified workout description for the user"
    )
    workout_type: Optional[Literal["run", "walk", "cycling", "rest", "interval"]] = Field(
        default=None,
        description="Type of workout activity"
    )
    duration_minutes: Optional[int] = Field(
        default=None,
        description="Workout duration in minutes",
        gt=0
    )
    intensity_zone: Optional[str] = Field(
        default=None,
        description="Training intensity zone like 'zone_1', 'zone_2', etc."
    )
    heart_rate_range: Optional[str] = Field(
        default=None,
        description="Target heart rate range like '80-90' or '100-110' BPM"
    )
    nutrition_fueling: Optional[str] = Field(
        default=None,
        description="Updated nutrition recommendations"
    )
    recovery_protocol: Optional[str] = Field(
        default=None,
        description="Updated recovery guidelines"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Updated explanation for the plan"
    )
    status: Optional[Literal["pending", "completed", "skipped", "partial"]] = Field(
        default=None,
        description="Completion status of the workout"
    )


@tool(args_schema=UpdatePlanInput)
async def update_coaching_plan(
    plan_id: str,
    todays_training: Optional[str] = None,
    workout_type: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    intensity_zone: Optional[str] = None,
    heart_rate_range: Optional[str] = None,
    nutrition_fueling: Optional[str] = None,
    recovery_protocol: Optional[str] = None,
    reasoning: Optional[str] = None,
    status: Optional[str] = None,
    config: RunnableConfig = None
) -> Dict:
    """
    Modify an existing training plan or update its completion status based on user feedback.

    Use this to mark plans as completed/skipped after user reports back, or adjust today's plan if requested.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Updating coaching plan {plan_id} for user {user_id}")

        async with async_session() as db:
            # Get existing recommendation
            result = await db.execute(
                select(CoachingRecommendation).where(
                    CoachingRecommendation.id == plan_id,
                    CoachingRecommendation.user_id == user_id
                )
            )
            recommendation = result.scalar_one_or_none()

            if not recommendation:
                return {"error": f"Plan {plan_id} not found for user {user_id}"}

            # Track what was updated
            updated_fields = []

            # Update training if provided
            if todays_training is not None:
                recommendation.todays_training = todays_training
                updated_fields.append("todays_training")

            # Update workout type if provided
            if workout_type is not None:
                recommendation.workout_type = workout_type
                updated_fields.append("workout_type")

            # Update duration if provided
            if duration_minutes is not None:
                recommendation.duration_minutes = duration_minutes
                updated_fields.append("duration_minutes")

            # Update intensity zone if provided
            if intensity_zone is not None:
                recommendation.intensity_zone = intensity_zone
                updated_fields.append("intensity_zone")

            # Update heart rate range if provided
            if heart_rate_range is not None:
                recommendation.heart_rate_range = heart_rate_range
                updated_fields.append("heart_rate_range")

            # Update nutrition if provided
            if nutrition_fueling is not None:
                recommendation.nutrition_fueling = nutrition_fueling
                updated_fields.append("nutrition_fueling")

            # Update recovery if provided
            if recovery_protocol is not None:
                recommendation.recovery_protocol = recovery_protocol
                updated_fields.append("recovery_protocol")

            # Update reasoning if provided
            if reasoning is not None:
                recommendation.reasoning = reasoning
                updated_fields.append("reasoning")

            # Update status if provided
            if status is not None:
                valid_statuses = ["pending", "completed", "skipped", "partial"]
                if status.lower() in valid_statuses:
                    recommendation.status = status.lower()
                    updated_fields.append("status")
                else:
                    return {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}

            # Update timestamp
            recommendation.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(recommendation)

            logger.info(f"✅ Plan updated: {plan_id} - Updated fields: {', '.join(updated_fields)}")

            return {
                "success": True,
                "plan_id": recommendation.id,
                "updated_fields": updated_fields,
                "workout_type": recommendation.workout_type,
                "duration_minutes": recommendation.duration_minutes,
                "intensity_zone": recommendation.intensity_zone,
                "heart_rate_range": recommendation.heart_rate_range,
                "status": recommendation.status,
                "message": f"Coaching plan updated successfully. Updated: {', '.join(updated_fields)}"
            }

    except Exception as e:
        logger.error(f"❌ Error updating plan: {e}")
        return {"error": str(e)}

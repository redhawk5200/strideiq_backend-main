"""
Create Plan Tool

Saves AI-generated coaching plan to database
"""

from typing import Dict, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
import cuid

from app.models.coaching_recommendation import CoachingRecommendation
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("create_plan_tool")


class CreatePlanInput(BaseModel):
    """Input schema for creating a coaching plan."""
    todays_training: str = Field(
        description="Detailed workout description for the user to read"
    )
    workout_type: Literal["run", "walk", "cycling", "rest", "interval"] = Field(
        description="Type of workout activity"
    )
    duration_minutes: int = Field(
        description="Workout duration in minutes",
        gt=0
    )
    intensity_zone: Optional[str] = Field(
        default=None,
        description="Training intensity zone like 'zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5'"
    )
    heart_rate_range: Optional[str] = Field(
        default=None,
        description="Target heart rate range like '80-90' or '100-110' BPM"
    )
    nutrition_fueling: Optional[str] = Field(
        default=None,
        description="Nutrition recommendations and fueling guidance"
    )
    recovery_protocol: Optional[str] = Field(
        default=None,
        description="Recovery guidelines including stretching, rest, sleep"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation of why this plan was prescribed based on user data and feedback"
    )


@tool(args_schema=CreatePlanInput)
async def create_coaching_plan(
    todays_training: str,
    workout_type: str,
    duration_minutes: int,
    intensity_zone: Optional[str] = None,
    heart_rate_range: Optional[str] = None,
    nutrition_fueling: Optional[str] = None,
    recovery_protocol: Optional[str] = None,
    reasoning: Optional[str] = None,
    config: RunnableConfig = None
) -> Dict:
    """
    Create and save a new daily training plan for the user.

    Use this ONLY after gathering feedback about previous workouts and confirming no plan exists for today.
    Always check get_previous_plans first to avoid duplicate plans.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Creating coaching plan for user {user_id}: {workout_type}, {duration_minutes}min")

        async with async_session() as db:
            # Create recommendation with agent-provided structured data
            recommendation = CoachingRecommendation(
                id=cuid.cuid(),
                user_id=user_id,
                recommendation_date=datetime.utcnow(),
                workout_type=workout_type,
                duration_minutes=duration_minutes,
                intensity_zone=intensity_zone,
                heart_rate_range=heart_rate_range,
                todays_training=todays_training,
                nutrition_fueling=nutrition_fueling,
                recovery_protocol=recovery_protocol,
                reasoning=reasoning,
                status="pending"
            )

            db.add(recommendation)
            await db.commit()
            await db.refresh(recommendation)

            logger.info(f"✅ Plan created: {recommendation.id} - {workout_type}, {duration_minutes}min")

            return {
                "success": True,
                "plan_id": recommendation.id,
                "workout_type": workout_type,
                "duration_minutes": duration_minutes,
                "intensity_zone": intensity_zone,
                "heart_rate_range": heart_rate_range,
                "message": "Coaching plan saved successfully"
            }

    except Exception as e:
        logger.error(f"❌ Error creating plan: {e}")
        return {"error": str(e)}

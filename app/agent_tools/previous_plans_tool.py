"""
Previous Plans Tool

Gets user's past coaching recommendations and compliance
"""

from typing import Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.future import select
from sqlalchemy import desc

from app.models.coaching_recommendation import CoachingRecommendation
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("previous_plans_tool")


class PreviousPlansInput(BaseModel):
    """Input schema for retrieving previous plans."""
    days: int = Field(
        default=7,
        description="How many days of training history to retrieve",
        gt=0,
        le=90
    )


@tool(args_schema=PreviousPlansInput)
async def get_previous_plans(days: int = 7, config: RunnableConfig = None) -> Dict:
    """
    Retrieve the user's recent training history, compliance patterns, and check if today's plan already exists.

    Use this when you need to understand what the user has been doing lately, how well they followed previous plans,
    or before creating a new plan to avoid duplicates.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Getting previous plans for user {user_id} (last {days} days)")

        async with async_session() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            result = await db.execute(
                select(CoachingRecommendation)
                .where(CoachingRecommendation.user_id == user_id)
                .where(CoachingRecommendation.recommendation_date >= cutoff_date)
                .order_by(desc(CoachingRecommendation.recommendation_date))
                .limit(10)
            )
            recommendations = result.scalars().all()

            if not recommendations:
                return {
                    "message": "No previous recommendations found",
                    "plans": []
                }

            # Check for today's plan
            today = datetime.utcnow().date()
            todays_plan = None

            plans = []
            for rec in recommendations:
                plan_date = rec.recommendation_date.date()
                plan_data = {
                    "plan_id": rec.id,
                    "date": plan_date.isoformat(),
                    "is_today": plan_date == today,
                    "workout_type": rec.workout_type,
                    "duration_minutes": rec.duration_minutes,
                    "intensity_zone": rec.intensity_zone,
                    "todays_training": rec.todays_training,
                    "nutrition_fueling": rec.nutrition_fueling,
                    "recovery_protocol": rec.recovery_protocol,
                    "reasoning": rec.reasoning,
                    "status": rec.status,
                    "compliance_notes": rec.compliance_notes
                }
                plans.append(plan_data)

                # Save today's plan separately
                if plan_date == today:
                    todays_plan = plan_data

            # Calculate compliance
            total = len(plans)
            completed = sum(1 for p in plans if p["status"] == "completed")
            compliance_rate = (completed / total * 100) if total > 0 else 0

            logger.info(f"✅ Found {total} plans, {compliance_rate:.0f}% compliance, today's plan: {todays_plan is not None}")

            return {
                "total_recommendations": total,
                "completed": completed,
                "compliance_rate": compliance_rate,
                "todays_plan": todays_plan,
                "plans": plans
            }

    except Exception as e:
        logger.error(f"❌ Error getting previous plans: {e}")
        return {"error": str(e)}

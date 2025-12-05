"""
Get Active Injuries Tool

Retrieves all active and recovering injuries for the user.
This should be checked BEFORE creating any workout plan.
"""

from typing import Dict
from datetime import datetime
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.future import select

from app.models.user_injury import UserInjury
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("get_active_injuries_tool")


class GetActiveInjuriesInput(BaseModel):
    """Input schema for getting active injuries."""
    include_recovering: bool = Field(
        default=True,
        description="Whether to include injuries marked as 'recovering' in addition to 'active' injuries"
    )


@tool(args_schema=GetActiveInjuriesInput)
async def get_active_injuries(include_recovering: bool = True, config: RunnableConfig = None) -> Dict:
    """
    Get all active and recovering injuries for the user.

    Use this BEFORE creating any workout plan to check if the user has any injuries
    that might affect training recommendations. This helps ensure workouts are safe
    and appropriate given the user's current injury status.

    Returns injury details including pain levels, affected areas, and activity restrictions.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Getting active injuries for user {user_id} (include_recovering={include_recovering})")

        async with async_session() as db:
            # Build query based on include_recovering
            if include_recovering:
                statuses = ["active", "recovering"]
            else:
                statuses = ["active"]

            result = await db.execute(
                select(UserInjury)
                .where(UserInjury.user_id == user_id)
                .where(UserInjury.status.in_(statuses))
                .order_by(UserInjury.injury_date.desc())
            )
            injuries = result.scalars().all()

            if not injuries:
                return {
                    "has_injuries": False,
                    "total_injuries": 0,
                    "injuries": [],
                    "message": "No active injuries found"
                }

            # Build injury list
            injury_list = []
            for injury in injuries:
                injury_data = {
                    "injury_id": injury.id,
                    "injury_type": injury.injury_type,
                    "affected_area": injury.affected_area,
                    "severity_level": injury.severity_level,
                    "current_pain_level": injury.current_pain_level,
                    "initial_pain_level": injury.initial_pain_level,
                    "status": injury.status,
                    "injury_date": injury.injury_date.date().isoformat(),
                    "days_since_injury": (datetime.utcnow().date() - injury.injury_date.date()).days,
                    "description": injury.description,
                    "symptoms": injury.symptoms,
                    "treatment_plan": injury.treatment_plan,
                    "activity_restrictions": injury.activity_restrictions,
                    "last_update": injury.last_update_date.date().isoformat() if injury.last_update_date else None
                }
                injury_list.append(injury_data)

            # Identify most severe injury
            most_severe = max(injuries, key=lambda x: x.current_pain_level if x.current_pain_level else 0)

            logger.info(f"✅ Found {len(injuries)} active injuries, highest pain: {most_severe.current_pain_level}/10")

            return {
                "has_injuries": True,
                "total_injuries": len(injuries),
                "injuries": injury_list,
                "most_severe_injury": {
                    "injury_type": most_severe.injury_type,
                    "affected_area": most_severe.affected_area,
                    "pain_level": most_severe.current_pain_level
                },
                "message": f"Found {len(injuries)} active/recovering injuries"
            }

    except Exception as e:
        logger.error(f"❌ Error getting active injuries: {e}")
        return {"error": str(e)}

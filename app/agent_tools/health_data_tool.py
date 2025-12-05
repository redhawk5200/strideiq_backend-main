"""
Health Data Tool

Gets user's current health metrics (VO2, heart rate, workouts)
"""

from typing import Dict
from datetime import datetime, timedelta
from pydantic import BaseModel
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.future import select
from sqlalchemy import desc, func

from app.models.user_profile import UserProfile
from app.models.vo2_max_estimate import VO2MaxEstimate
from app.models.heart_rate_sample import HeartRateSample
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("health_data_tool")


class HealthDataInput(BaseModel):
    """Input schema for retrieving health data (no parameters needed)."""
    pass


@tool(args_schema=HealthDataInput)
async def get_user_health_data(config: RunnableConfig = None) -> Dict:
    """
    Retrieve the user's current health snapshot including latest VO2 max and recent heart rate averages.

    Use this to assess current fitness level and physiological readiness before prescribing workouts.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Getting health data for user {user_id}")

        # Get database session
        async with async_session() as db:
            # Get profile
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()

            if not profile:
                return {"error": "User profile not found"}

            # Get latest VO2 max
            vo2_result = await db.execute(
                select(VO2MaxEstimate)
                .where(VO2MaxEstimate.user_id == user_id)
                .order_by(desc(VO2MaxEstimate.measured_at))
                .limit(1)
            )
            vo2 = vo2_result.scalar_one_or_none()

            # # Get recent workouts (last 3)
            # workout_result = await db.execute(
            #     select(WorkoutSession)
            #     .where(WorkoutSession.user_id == user_id)
            #     .order_by(desc(WorkoutSession.start_time))
            #     .limit(3)
            # )
            # workouts = workout_result.scalars().all()

            # Get average heart rate from last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            hr_result = await db.execute(
                select(func.avg(HeartRateSample.bpm))
                .where(HeartRateSample.user_id == user_id)
                .where(HeartRateSample.captured_at >= yesterday)
            )
            avg_hr = hr_result.scalar()

            data = {
                "first_name": profile.first_name,
                "age": profile.age,
                "vo2_max": vo2.ml_per_kg_min if vo2 else None,
                "vo2_measured_at": vo2.measured_at.isoformat() if vo2 else None,
                "avg_heart_rate_24h": round(avg_hr) if avg_hr else None,
                # "recent_workouts": [
                #     {
                #         "date": w.start_time.date().isoformat(),
                #         "type": w.activity_type,
                #         "duration_min": round(w.duration_seconds / 60) if w.duration_seconds else 0,
                #         "distance_miles": w.distance_miles
                #     }
                #     for w in workouts
                # ]
            }

            logger.info(f"✅ Health data retrieved: VO2={data['vo2_max']}")
            return data

    except Exception as e:
        logger.error(f"❌ Error getting health data: {e}")
        return {"error": str(e)}

"""
Workout Details Tool

Gets detailed workout history and statistics
"""

from typing import Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.future import select
from sqlalchemy import desc

from app.models.workout_session import WorkoutSession
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("workout_details_tool")


class WorkoutDetailsInput(BaseModel):
    """Input schema for retrieving workout details."""
    days_back: int = Field(
        default=7,
        description="How many days of workout history to retrieve",
        gt=0,
        le=90
    )


@tool(args_schema=WorkoutDetailsInput)
async def get_workout_details(days_back: int = 7, config: RunnableConfig = None) -> Dict:
    """
    Retrieve actual completed workouts with performance metrics like heart rate, distance, duration, and calories.

    Use this to compare user's actual performance against previous workouts or to analyze training load and patterns.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Getting workout details for user {user_id} (last {days_back} days)")

        async with async_session() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)

            # Get recent workouts
            workout_result = await db.execute(
                select(WorkoutSession)
                .where(WorkoutSession.user_id == user_id)
                .where(WorkoutSession.start_time >= cutoff_date)
                .order_by(desc(WorkoutSession.start_time))
                .limit(20)
            )
            workouts = workout_result.scalars().all()

            if not workouts:
                return {
                    "message": f"No workouts found in the last {days_back} days",
                    "workouts": [],
                    "stats": {}
                }

            # Build detailed workout list
            workout_list = []
            for w in workouts:
                workout_list.append({
                    "date": w.start_time.date().isoformat(),
                    "activity_type": w.activity_type,
                    "duration_minutes": round(w.duration_seconds / 60) if w.duration_seconds else 0,
                    "distance_miles": round(w.distance_miles, 2) if w.distance_miles else None,
                    "calories": round(w.calories, 0) if w.calories else None,
                    "avg_heart_rate": w.avg_heart_rate,
                    "max_heart_rate": w.max_heart_rate
                })

            # Calculate statistics
            total_workouts = len(workouts)
            total_distance = sum(w.distance_miles for w in workouts if w.distance_miles)
            total_duration = sum(w.duration_seconds for w in workouts if w.duration_seconds) / 60  # minutes
            total_calories = sum(w.calories for w in workouts if w.calories)

            # Group by activity type
            activity_counts = {}
            for w in workouts:
                activity = w.activity_type or "Unknown"
                activity_counts[activity] = activity_counts.get(activity, 0) + 1

            stats = {
                "total_workouts": total_workouts,
                "total_distance_miles": round(total_distance, 2) if total_distance else 0,
                "total_duration_minutes": round(total_duration, 0),
                "total_calories": round(total_calories, 0) if total_calories else 0,
                "avg_duration_minutes": round(total_duration / total_workouts, 0) if total_workouts > 0 else 0,
                "activity_breakdown": activity_counts,
                "days_analyzed": days_back
            }

            logger.info(f"✅ Workout details retrieved: {total_workouts} workouts in {days_back} days")

            return {
                "workouts": workout_list,
                "stats": stats
            }

    except Exception as e:
        logger.error(f"❌ Error getting workout details: {e}")
        return {"error": str(e)}

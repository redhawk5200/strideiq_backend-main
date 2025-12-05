"""
User Profile Tool

Gets complete user profile including goals, preferences, and weight data
"""

from typing import Dict
from pydantic import BaseModel
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig

from app.services.onboarding_service import OnboardingService
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("user_profile_tool")


class UserProfileInput(BaseModel):
    """Input schema for retrieving user profile (no parameters needed)."""
    pass


@tool(args_schema=UserProfileInput)
async def get_user_profile(config: RunnableConfig = None) -> Dict:
    """
    Retrieve the user's personal information, fitness goals, training preferences, and current/target weight.

    Use this when you need to understand the user's objectives, constraints, or personalize recommendations.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Getting user profile for user {user_id}")

        async with async_session() as db:
            # Get onboarding status
            status_data = await OnboardingService.get_onboarding_status(db, user_id)

            # Get weight data
            current_weight_data = await OnboardingService.get_current_weight(db, user_id)
            target_weight_data = await OnboardingService.get_target_weight(db, user_id)

            profile = status_data.get("profile")
            if not profile:
                return {"error": "User profile not found"}

            # Build profile data
            profile_info = {
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "age": profile.age,
                "gender": profile.gender,
                "height_inches": profile.height_inches,
                "unit_preference": profile.unit_preference
            }

            # Goals
            goals = []
            for goal in status_data.get("goals", []):
                goals.append({
                    "goal_type": goal.goal_type,
                    "description": goal.description,
                    "target_value": goal.target_value,
                    "unit": goal.unit,
                    "target_date": goal.target_date.isoformat() if goal.target_date else None,
                    "active": goal.active
                })

            # Training preferences
            training_prefs = status_data.get("training_preferences")
            training_preferences = None
            if training_prefs:
                training_preferences = {
                    "training_level": training_prefs.training_level,
                    "days_per_week": training_prefs.days_per_week,
                    "sessions_per_day": training_prefs.sessions_per_day,
                    "preferred_time_window": training_prefs.preferred_time_window
                }

            # Weight data
            current_weight_lbs = current_weight_data.value_lbs if current_weight_data else None
            target_weight_lbs = float(target_weight_data["target_value"]) if target_weight_data and target_weight_data["target_value"] else None
            weight_goal_type = target_weight_data["goal_type"] if target_weight_data else None

            data = {
                "profile": profile_info,
                "goals": goals,
                "training_preferences": training_preferences,
                "current_weight_lbs": current_weight_lbs,
                "target_weight_lbs": target_weight_lbs,
                "weight_goal_type": weight_goal_type
            }

            logger.info(f"✅ User profile retrieved: {profile.first_name}, {len(goals)} goals")
            return data

    except Exception as e:
        logger.error(f"❌ Error getting user profile: {e}")
        return {"error": str(e)}

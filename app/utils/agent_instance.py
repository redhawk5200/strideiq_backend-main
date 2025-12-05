"""
Global Agent Instance

Single agent instance initialized with tools on startup.
"""

from app.services.ai_coaching_agent import AICoachingAgent
from app.agent_tools.health_data_tool import get_user_health_data
from app.agent_tools.previous_plans_tool import get_previous_plans
from app.agent_tools.vo2_trends_tool import get_vo2_trends
from app.agent_tools.workout_details_tool import get_workout_details
from app.agent_tools.user_profile_tool import get_user_profile
from app.agent_tools.create_plan_tool import create_coaching_plan
from app.agent_tools.update_plan_tool import update_coaching_plan

# Injury tracking tools
from app.agent_tools.report_injury_tool import report_injury
from app.agent_tools.update_injury_tool import update_injury_status
from app.agent_tools.get_active_injuries_tool import get_active_injuries
from app.agent_tools.get_injury_history_tool import get_injury_history

from app.core.logger import get_logger

logger = get_logger("agent_instance")

# Global agent instance
agent = AICoachingAgent()


def initialize_agent():
    """Initialize the agent with tools. Call once on startup."""

    tools = [
        # User data and health tools
        get_user_health_data,
        get_user_profile,
        get_previous_plans,
        get_vo2_trends,
        get_workout_details,

        # Coaching plan tools
        create_coaching_plan,
        update_coaching_plan,

        # Injury tracking tools
        report_injury,
        update_injury_status,
        get_active_injuries,
        get_injury_history,
    ]

    agent.initialize(tools=tools)
    logger.info("✅ Global agent initialized with 11 tools (7 existing + 4 injury tracking)")

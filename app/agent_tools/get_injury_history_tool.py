"""
Get Injury History Tool

Retrieves user's injury history to analyze patterns and recurring issues.
"""

from typing import Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.future import select
from sqlalchemy import desc, func

from app.models.user_injury import UserInjury
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("get_injury_history_tool")


class InjuryHistoryInput(BaseModel):
    """Input schema for getting injury history."""
    days_back: int = Field(
        default=180,
        description="How many days of injury history to retrieve (default 180 days / 6 months)",
        gt=0,
        le=365
    )
    include_recovered: bool = Field(
        default=True,
        description="Whether to include recovered injuries in the history"
    )


@tool(args_schema=InjuryHistoryInput)
async def get_injury_history(days_back: int = 180, include_recovered: bool = True, config: RunnableConfig = None) -> Dict:
    """
    Get user's injury history and patterns over time.

    Use this to identify recurring injuries, chronic issues, or patterns that might
    inform training adjustments (e.g., recurring knee pain suggests need for strength work).
    Helps with long-term injury prevention and understanding user's injury patterns.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Getting injury history for user {user_id} (last {days_back} days)")

        async with async_session() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)

            # Build query
            query = select(UserInjury).where(
                UserInjury.user_id == user_id,
                UserInjury.injury_date >= cutoff_date
            )

            if not include_recovered:
                query = query.where(UserInjury.status != "recovered")

            query = query.order_by(desc(UserInjury.injury_date))

            result = await db.execute(query)
            injuries = result.scalars().all()

            if not injuries:
                return {
                    "total_injuries": 0,
                    "injuries": [],
                    "patterns": {},
                    "message": f"No injuries found in the last {days_back} days"
                }

            # Build injury list
            injury_list = []
            for injury in injuries:
                injury_data = {
                    "injury_id": injury.id,
                    "injury_type": injury.injury_type,
                    "affected_area": injury.affected_area,
                    "severity_level": injury.severity_level,
                    "status": injury.status,
                    "injury_date": injury.injury_date.date().isoformat(),
                    "pain_range": f"{injury.initial_pain_level} → {injury.current_pain_level}",
                    "days_to_recover": (injury.actual_recovery_date.date() - injury.injury_date.date()).days if injury.actual_recovery_date else None,
                    "description": injury.description
                }
                injury_list.append(injury_data)

            # Analyze patterns

            # Count by injury type
            injury_type_counts = {}
            for injury in injuries:
                injury_type_counts[injury.injury_type] = injury_type_counts.get(injury.injury_type, 0) + 1

            # Count by affected area
            affected_area_counts = {}
            for injury in injuries:
                affected_area_counts[injury.affected_area] = affected_area_counts.get(injury.affected_area, 0) + 1

            # Identify recurring issues (same injury type appearing multiple times)
            recurring_injuries = []
            for injury_type, count in injury_type_counts.items():
                if count > 1:
                    # Get all instances of this injury type
                    instances = [inj for inj in injuries if inj.injury_type == injury_type]
                    recurring_injuries.append({
                        "injury_type": injury_type,
                        "occurrences": count,
                        "most_common_area": max(set([inj.affected_area for inj in instances]), key=[inj.affected_area for inj in instances].count)
                    })

            # Calculate stats
            total_injuries = len(injuries)
            active_count = sum(1 for inj in injuries if inj.status == "active")
            recovering_count = sum(1 for inj in injuries if inj.status == "recovering")
            recovered_count = sum(1 for inj in injuries if inj.status == "recovered")
            chronic_count = sum(1 for inj in injuries if inj.status == "chronic")

            # Average recovery time (for recovered injuries)
            recovered_injuries = [inj for inj in injuries if inj.actual_recovery_date]
            if recovered_injuries:
                recovery_times = [(inj.actual_recovery_date.date() - inj.injury_date.date()).days for inj in recovered_injuries]
                avg_recovery_days = sum(recovery_times) / len(recovery_times)
            else:
                avg_recovery_days = None

            logger.info(f"✅ Injury history retrieved: {total_injuries} injuries, {len(recurring_injuries)} recurring patterns")

            return {
                "total_injuries": total_injuries,
                "injuries": injury_list,
                "status_breakdown": {
                    "active": active_count,
                    "recovering": recovering_count,
                    "recovered": recovered_count,
                    "chronic": chronic_count
                },
                "patterns": {
                    "injury_type_counts": injury_type_counts,
                    "affected_area_counts": affected_area_counts,
                    "recurring_injuries": recurring_injuries,
                    "average_recovery_days": round(avg_recovery_days) if avg_recovery_days else None
                },
                "days_analyzed": days_back,
                "message": f"Found {total_injuries} injuries in the last {days_back} days"
            }

    except Exception as e:
        logger.error(f"❌ Error getting injury history: {e}")
        return {"error": str(e)}

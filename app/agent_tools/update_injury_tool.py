"""
Update Injury Tool

Allows the agent to update the status and progress of existing injuries.
"""

from typing import Dict, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.future import select
import cuid

from app.models.user_injury import UserInjury
from app.models.injury_update import InjuryUpdate
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("update_injury_tool")


class UpdateInjuryInput(BaseModel):
    """Input schema for updating an injury."""
    injury_id: str = Field(
        description="ID of the injury to update"
    )
    pain_level: Optional[int] = Field(
        default=None,
        description="Current pain level on scale 1-10",
        ge=1,
        le=10
    )
    improvement_level: Optional[Literal["improving", "same", "worse"]] = Field(
        default=None,
        description="Whether the injury is getting better (improving), staying the same (same), or getting worse (worse)"
    )
    status: Optional[Literal["active", "recovering", "recovered", "chronic"]] = Field(
        default=None,
        description="Current status: active (currently injured), recovering (getting better), recovered (fully healed), chronic (long-term ongoing)"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Update notes about how the injury feels, user's feedback, progress observations"
    )
    activities_performed: Optional[str] = Field(
        default=None,
        description="What activities the user has done since last update (e.g., 'walked 2 miles, did stretching')"
    )
    pain_triggers: Optional[str] = Field(
        default=None,
        description="Activities or movements that caused pain (e.g., 'running uphill, jumping')"
    )


@tool(args_schema=UpdateInjuryInput)
async def update_injury_status(
    injury_id: str,
    pain_level: Optional[int] = None,
    improvement_level: Optional[str] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    activities_performed: Optional[str] = None,
    pain_triggers: Optional[str] = None,
    config: RunnableConfig = None
) -> Dict:
    """
    Update the status and progress of an existing injury.

    Use this when a user provides feedback about how their injury is feeling,
    whether it's getting better or worse, or to mark it as recovered.
    This creates a timeline of recovery progress.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Updating injury {injury_id} for user {user_id}")

        async with async_session() as db:
            # Get the injury
            result = await db.execute(
                select(UserInjury).where(
                    UserInjury.id == injury_id,
                    UserInjury.user_id == user_id
                )
            )
            injury = result.scalar_one_or_none()

            if not injury:
                return {"error": f"Injury {injury_id} not found for user {user_id}"}

            # Track what was updated
            updated_fields = []

            # Update pain level
            if pain_level is not None:
                injury.current_pain_level = pain_level
                updated_fields.append("pain_level")

            # Update status
            if status is not None:
                injury.status = status
                updated_fields.append("status")

                # If recovered, set recovery date
                if status == "recovered" and not injury.actual_recovery_date:
                    injury.actual_recovery_date = datetime.utcnow()
                    updated_fields.append("recovery_date")

            # Update last update date
            injury.last_update_date = datetime.utcnow()

            # Create an injury update record for timeline
            injury_update = InjuryUpdate(
                id=cuid.cuid(),
                injury_id=injury_id,
                user_id=user_id,
                update_date=datetime.utcnow(),
                pain_level=pain_level,
                status=status,
                notes=notes,
                improvement_level=improvement_level,
                activities_performed={"activities": activities_performed} if activities_performed else None,
                pain_triggers={"triggers": pain_triggers} if pain_triggers else None
            )

            db.add(injury_update)
            await db.commit()
            await db.refresh(injury)

            logger.info(f"✅ Injury updated: {injury_id} - Pain: {injury.current_pain_level}/10, Status: {injury.status}, Improvement: {improvement_level}")

            return {
                "success": True,
                "injury_id": injury.id,
                "injury_type": injury.injury_type,
                "affected_area": injury.affected_area,
                "current_pain_level": injury.current_pain_level,
                "status": injury.status,
                "improvement_level": improvement_level,
                "updated_fields": updated_fields,
                "message": f"Injury status updated successfully. Updated: {', '.join(updated_fields)}"
            }

    except Exception as e:
        logger.error(f"❌ Error updating injury: {e}")
        return {"error": str(e)}

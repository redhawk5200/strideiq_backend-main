"""
Report Injury Tool

Allows the agent to document new injuries or pain reported by users.
"""

from typing import Dict, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
import cuid

from app.models.user_injury import UserInjury
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("report_injury_tool")


class ReportInjuryInput(BaseModel):
    """Input schema for reporting a new injury."""
    injury_type: str = Field(
        description="Type of injury (e.g., 'shin_splints', 'runners_knee', 'plantar_fasciitis', 'achilles_tendonitis', 'it_band_syndrome', 'calf_strain', 'ankle_sprain', 'hip_flexor_strain', 'lower_back_pain', 'muscle_soreness')"
    )
    affected_area: str = Field(
        description="Specific body part affected (e.g., 'left_knee', 'right_ankle', 'lower_back', 'left_shin', 'right_calf')"
    )
    severity_level: Literal["mild", "moderate", "severe"] = Field(
        description="Severity of the injury: mild (minor discomfort), moderate (significant pain), severe (serious injury)"
    )
    pain_level: int = Field(
        description="Pain level on a scale from 1-10, where 1 is minimal and 10 is extreme",
        ge=1,
        le=10
    )
    description: str = Field(
        description="Detailed description of the injury, symptoms, and when/how it occurred"
    )
    injury_date: Optional[str] = Field(
        default=None,
        description="When the injury occurred in ISO format (YYYY-MM-DD). If not specified, uses today's date."
    )
    symptoms: Optional[str] = Field(
        default=None,
        description="Specific symptoms like swelling, stiffness, pain during activity, pain after activity"
    )
    treatment_plan: Optional[str] = Field(
        default=None,
        description="Initial treatment plan like rest, ice, compression, elevation, physical therapy"
    )


@tool(args_schema=ReportInjuryInput)
async def report_injury(
    injury_type: str,
    affected_area: str,
    severity_level: str,
    pain_level: int,
    description: str,
    injury_date: Optional[str] = None,
    symptoms: Optional[str] = None,
    treatment_plan: Optional[str] = None,
    config: RunnableConfig = None
) -> Dict:
    """
    Report a new injury or pain that the user is experiencing.

    Use this when a user mentions pain, injury, discomfort, or any physical issue
    that might affect their training. Always ask clarifying questions first
    (pain level, when it started, symptoms) before reporting the injury.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Reporting injury for user {user_id}: {injury_type} - {affected_area}")

        # Parse injury date or use today
        if injury_date:
            try:
                injury_datetime = datetime.fromisoformat(injury_date)
            except ValueError:
                injury_datetime = datetime.utcnow()
        else:
            injury_datetime = datetime.utcnow()

        async with async_session() as db:
            # Create injury record
            injury = UserInjury(
                id=cuid.cuid(),
                user_id=user_id,
                injury_type=injury_type,
                affected_area=affected_area,
                severity_level=severity_level,
                initial_pain_level=pain_level,
                current_pain_level=pain_level,
                injury_date=injury_datetime,
                reported_date=datetime.utcnow(),
                status="active",
                description=description,
                symptoms=symptoms,
                treatment_plan=treatment_plan,
                last_update_date=datetime.utcnow()
            )

            db.add(injury)
            await db.commit()
            await db.refresh(injury)

            logger.info(f"✅ Injury reported: {injury.id} - {injury_type} ({severity_level}, pain {pain_level}/10)")

            return {
                "success": True,
                "injury_id": injury.id,
                "injury_type": injury_type,
                "affected_area": affected_area,
                "severity_level": severity_level,
                "pain_level": pain_level,
                "status": "active",
                "message": f"Injury reported successfully: {injury_type} in {affected_area}"
            }

    except Exception as e:
        logger.error(f"❌ Error reporting injury: {e}")
        return {"error": str(e)}

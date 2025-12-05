"""
VO2 Trends Tool

Gets user's VO2 max trend analysis and measurements
"""

from typing import Dict
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.future import select
from sqlalchemy import desc

from app.models.vo2_max_estimate import VO2MaxEstimate
from app.services.vo2_analysis_service import VO2MaxAnalysisService
from app.database.connection import async_session
from app.core.logger import get_logger

logger = get_logger("vo2_trends_tool")


class VO2TrendsInput(BaseModel):
    """Input schema for retrieving VO2 trends."""
    days_back: int = Field(
        default=90,
        description="How many days of VO2 history to analyze for trends",
        gt=0,
        le=365
    )


@tool(args_schema=VO2TrendsInput)
async def get_vo2_trends(days_back: int = 90, config: RunnableConfig = None) -> Dict:
    """
    Analyze the user's cardiovascular fitness progression over time through VO2 max measurements.

    Use this to celebrate improvements, identify fitness trends, or support training decisions with data.
    """
    try:
        # Get user_id from config
        user_id = config.get("configurable", {}).get("user_id")

        if not user_id:
            return {"error": "user_id not found in config"}

        logger.info(f"🔧 Getting VO2 trends for user {user_id} (last {days_back} days)")

        async with async_session() as db:
            # Get trend analysis
            trend_analysis = await VO2MaxAnalysisService.get_vo2_trend_analysis(
                db, user_id, days_back
            )

            # Get recent measurements
            vo2_result = await db.execute(
                select(VO2MaxEstimate)
                .where(VO2MaxEstimate.user_id == user_id)
                .order_by(desc(VO2MaxEstimate.measured_at))
                .limit(10)
            )
            vo2_records = vo2_result.scalars().all()

            data = {
                "trend_analysis": trend_analysis,
                "recent_measurements": [
                    {
                        "value": record.ml_per_kg_min,
                        "measured_at": record.measured_at.isoformat(),
                        "estimation_method": record.estimation_method
                    }
                    for record in vo2_records
                ],
                "total_measurements": len(vo2_records)
            }

            logger.info(f"✅ VO2 trends retrieved: {len(vo2_records)} measurements")
            return data

    except Exception as e:
        logger.error(f"❌ Error getting VO2 trends: {e}")
        return {"error": str(e)}

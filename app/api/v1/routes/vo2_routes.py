from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database.connection import get_db
from app.api.v1.controllers.vo2_controller import VO2MaxController

router = APIRouter(prefix="/vo2-analysis", tags=["VO₂max Analysis"])


@router.get("/comprehensive")
async def get_comprehensive_vo2_analysis(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days_back: int = Query(
        90, 
        ge=7, 
        le=365, 
        description="Number of days to analyze for trends"
    )
):
    """
    Get comprehensive VO₂max analysis with AI-powered insights.
    
    This endpoint provides:
    - Current VO₂max with fitness category and percentile
    - Trend analysis over specified period
    - Supporting health metrics correlation
    - Comprehensive fitness score
    - AI-generated personalized insights and recommendations
    
    Requires:
    - Authentication
    - User profile with age and gender
    - At least one VO₂max measurement
    """
    return await VO2MaxController.get_comprehensive_vo2_analysis(
        request, db, days_back
    )


@router.get("/trends")
async def get_vo2_trends(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days_back: int = Query(
        90, 
        ge=7, 
        le=365, 
        description="Number of days to analyze for trends"
    )
):
    """
    Get VO₂max trend analysis without AI insights.
    
    This endpoint provides:
    - Trend analysis over specified period
    - Recent VO₂max measurements
    - Statistical trend information
    
    Requires:
    - Authentication
    - At least one VO₂max measurement
    """
    return await VO2MaxController.get_vo2_trends_only(
        request, db, days_back
    )


@router.get("/benchmarks")
async def get_fitness_benchmarks(
    request: Request,
    age: Optional[int] = Query(
        None, 
        ge=18, 
        le=100, 
        description="Age for benchmark calculation"
    ),
    gender: Optional[str] = Query(
        None, 
        regex="^(male|female)$", 
        description="Gender for benchmark calculation"
    )
):
    """
    Get VO₂max fitness benchmarks for demographics.
    
    If age and gender are not provided, uses authenticated user's profile.
    
    Returns fitness category thresholds and descriptions for:
    - Excellent
    - Good  
    - Average
    - Below Average
    - Poor
    """
    return await VO2MaxController.get_fitness_benchmarks(
        request, age, gender
    )


@router.get("/quick-assessment")
async def get_quick_vo2_assessment(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a quick VO₂max fitness assessment.
    
    Returns basic fitness category and percentile for the most recent measurement.
    Lightweight alternative to comprehensive analysis.
    """
    full_analysis = await VO2MaxController.get_comprehensive_vo2_analysis(
        request, db, days_back=30
    )
    
    if full_analysis["status"] != "success":
        return full_analysis
    
    return {
        "status": "success",
        "user_id": full_analysis["user_profile"]["user_id"],
        "current_vo2": full_analysis["current_vo2_max"]["value"],
        "measured_at": full_analysis["current_vo2_max"]["measured_at"],
        "fitness_category": full_analysis["fitness_assessment"]["category"],
        "percentile": full_analysis["fitness_assessment"]["percentile"],
        "age_bracket": full_analysis["fitness_assessment"]["age_bracket"],
        "overall_score": full_analysis["comprehensive_score"]["total_score"],
        "quick_summary": full_analysis.get("quick_summary", {})
    }
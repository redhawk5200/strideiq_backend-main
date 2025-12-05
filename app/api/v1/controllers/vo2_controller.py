from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, Optional

from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.vo2_max_estimate import VO2MaxEstimate
from app.services.vo2_analysis_service import VO2MaxAnalysisService
from app.services.vo2_insights_service import VO2InsightsGenerator
from app.core.logger import get_logger

logger = get_logger("vo2_controller")


class VO2MaxController:
    """Controller for VO₂max analysis and insights."""
    
    @staticmethod
    async def get_comprehensive_vo2_analysis(
        request: Request,
        db: AsyncSession,
        days_back: int = 90
    ) -> Dict:
        """Get comprehensive VO₂max analysis with LLM-generated insights."""
        
        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )
            
            user = request.state.user
            
            # Load user profile for demographic data
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user.id)
            )
            profile = profile_result.scalar_one_or_none()
            
            # Get the latest VO₂max estimate
            latest_vo2_query = select(VO2MaxEstimate).where(
                VO2MaxEstimate.user_id == user.id
            ).order_by(VO2MaxEstimate.measured_at.desc()).limit(1)
            
            latest_vo2_result = await db.execute(latest_vo2_query)
            latest_vo2 = latest_vo2_result.scalar_one_or_none()
            
            #validation and check for vo2
            if not latest_vo2:
                return {
                    "status": "no_data",
                    "message": "No VO₂max data available for analysis",
                    "user_id": user.id
                }
            
            # Validate user demographics
            if not profile or not profile.age or not profile.gender:
                return {
                    "status": "incomplete_profile",
                    "message": "Age and gender information required for comprehensive analysis",
                    "current_vo2": latest_vo2.ml_per_kg_min,
                    "measured_at": latest_vo2.measured_at.isoformat()
                }
            
            # Get fitness category and benchmarks
            fitness_category = VO2MaxAnalysisService.calculate_fitness_category(
                latest_vo2.ml_per_kg_min,
                profile.age,
                profile.gender
            )
            
            # Get trend analysis
            trend_analysis = await VO2MaxAnalysisService.get_vo2_trend_analysis(
                db, user.id, days_back
            )
            
            # Get supporting health metrics
            supporting_metrics = await VO2MaxAnalysisService.get_supporting_metrics(
                db, user.id, days_back=30
            )
            
            # Calculate comprehensive score
            comprehensive_score = VO2MaxAnalysisService.calculate_comprehensive_score(
                latest_vo2.ml_per_kg_min,
                fitness_category,
                trend_analysis,
                supporting_metrics
            )
            
            # Generate LLM insights
            insights_generator = VO2InsightsGenerator()
            
            # Prepare context for LLM
            context = insights_generator.prepare_insight_context(
                user_profile={
                    'age': profile.age,
                    'gender': profile.gender,
                    'email': user.email
                },
                vo2_analysis={
                    'latest_vo2': latest_vo2.ml_per_kg_min,
                    'category': fitness_category['category'],
                    'percentile': fitness_category['percentile'],
                    'age_bracket': fitness_category['age_bracket'],
                    'next_level': fitness_category['next_level']
                },
                trend_analysis=trend_analysis,
                supporting_metrics=supporting_metrics,
                comprehensive_score=comprehensive_score
            )
            
            # Generate insights
            llm_insights = await insights_generator.generate_insights(context)
            quick_summary = insights_generator.generate_quick_summary(context)
            
            # Compile comprehensive response
            response = {
                "status": "success",
                "user_profile": {
                    "user_id": user.id,
                    "age": profile.age,
                    "gender": profile.gender,
                    "email": user.email
                },
                "current_vo2_max": {
                    "value": latest_vo2.ml_per_kg_min,
                    "measured_at": latest_vo2.measured_at.isoformat(),
                    "estimation_method": latest_vo2.estimation_method,
                    "context": latest_vo2.context
                },
                "fitness_assessment": {
                    "category": fitness_category['category'],
                    "percentile": fitness_category['percentile'],
                    "age_bracket": fitness_category['age_bracket'],
                    "benchmarks": fitness_category['benchmarks'],
                    "next_level_target": fitness_category['next_level']
                },
                "trend_analysis": trend_analysis,
                "supporting_metrics": supporting_metrics,
                "comprehensive_score": comprehensive_score,
                "quick_summary": quick_summary,
                "ai_insights": llm_insights,
                "analysis_parameters": {
                    "trend_analysis_days": days_back,
                    "supporting_metrics_days": 30,
                    "analysis_date": latest_vo2.measured_at.isoformat()
                }
            }
            
            logger.info(f"Generated comprehensive VO₂max analysis for user {user.email}")
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in comprehensive VO₂max analysis: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate VO₂max analysis"
            )
    
    @staticmethod
    async def get_vo2_trends_only(
        request: Request,
        db: AsyncSession,
        days_back: int = 90
    ) -> Dict:
        """Get VO₂max trend analysis without LLM insights."""
        
        try:
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )
            
            user = request.state.user
            
            # Get trend analysis
            trend_analysis = await VO2MaxAnalysisService.get_vo2_trend_analysis(
                db, user.id, days_back
            )
            
            # Get all VO₂max estimates for detailed view
            vo2_query = select(VO2MaxEstimate).where(
                VO2MaxEstimate.user_id == user.id
            ).order_by(VO2MaxEstimate.measured_at.desc()).limit(50)
            
            vo2_result = await db.execute(vo2_query)
            vo2_records = vo2_result.scalars().all()
            
            return {
                "status": "success",
                "user_id": user.id,
                "trend_analysis": trend_analysis,
                "recent_measurements": [
                    {
                        "value": record.ml_per_kg_min,
                        "measured_at": record.measured_at.isoformat(),
                        "estimation_method": record.estimation_method,
                        "context": record.context
                    }
                    for record in vo2_records
                ],
                "analysis_parameters": {
                    "days_back": days_back,
                    "total_measurements": len(vo2_records)
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in VO₂max trend analysis: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get VO₂max trends"
            )
    
    @staticmethod
    async def get_fitness_benchmarks(
        request: Request,
        age: Optional[int] = None,
        gender: Optional[str] = None
    ) -> Dict:
        """Get VO₂max fitness benchmarks for specified or user demographics."""
        
        try:
            # Use provided demographics or get from authenticated user
            target_age = age
            target_gender = gender
            
            if not target_age or not target_gender:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Age and gender parameters are required for fitness benchmarks"
                )
            
            # Get age bracket and benchmarks
            age_bracket = VO2MaxAnalysisService.get_age_bracket(target_age)
            
            # Get benchmarks for the demographic
            from app.services.vo2_analysis_service import VO2_BENCHMARKS
            
            gender_key = target_gender.lower()
            if gender_key not in VO2_BENCHMARKS:
                gender_key = 'male'  # Default fallback
            
            benchmarks = VO2_BENCHMARKS[gender_key][age_bracket]
            
            return {
                "demographics": {
                    "age": target_age,
                    "gender": target_gender,
                    "age_bracket": age_bracket
                },
                "benchmarks": benchmarks,
                "categories": {
                    "excellent": f"{benchmarks['excellent']}+ ml/kg/min",
                    "good": f"{benchmarks['good']}-{benchmarks['excellent']-0.1} ml/kg/min",
                    "average": f"{benchmarks['average']}-{benchmarks['good']-0.1} ml/kg/min",
                    "below_average": f"{benchmarks['below_average']}-{benchmarks['average']-0.1} ml/kg/min",
                    "poor": f"<{benchmarks['below_average']} ml/kg/min"
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting fitness benchmarks: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get fitness benchmarks"
            )
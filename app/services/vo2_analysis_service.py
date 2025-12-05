from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc
from statistics import mean, stdev
import numpy as np
from sklearn.linear_model import LinearRegression

from app.models.user import User
from app.models.vo2_max_estimate import VO2MaxEstimate
from app.models.heart_rate_sample import HeartRateSample
from app.models.sleep_session import SleepSession
from app.models.step_minute import StepMinute
from app.core.logger import get_logger

logger = get_logger("vo2_analysis_service")


# VO₂max benchmarks by age and gender (ml/kg/min)
VO2_BENCHMARKS = {
    'male': {
        '20-29': {'excellent': 56, 'good': 51, 'average': 45, 'below_average': 41, 'poor': 37},
        '30-39': {'excellent': 54, 'good': 48, 'average': 42, 'below_average': 39, 'poor': 35},
        '40-49': {'excellent': 52, 'good': 46, 'average': 40, 'below_average': 36, 'poor': 32},
        '50-59': {'excellent': 48, 'good': 43, 'average': 37, 'below_average': 33, 'poor': 29},
        '60-69': {'excellent': 45, 'good': 39, 'average': 33, 'below_average': 29, 'poor': 25},
        '70+': {'excellent': 42, 'good': 36, 'average': 30, 'below_average': 26, 'poor': 22}
    },
    'female': {
        '20-29': {'excellent': 49, 'good': 43, 'average': 36, 'below_average': 32, 'poor': 28},
        '30-39': {'excellent': 47, 'good': 41, 'average': 34, 'below_average': 30, 'poor': 26},
        '40-49': {'excellent': 45, 'good': 39, 'average': 32, 'below_average': 28, 'poor': 24},
        '50-59': {'excellent': 42, 'good': 36, 'average': 29, 'below_average': 25, 'poor': 21},
        '60-69': {'excellent': 39, 'good': 33, 'average': 26, 'below_average': 22, 'poor': 18},
        '70+': {'excellent': 36, 'good': 30, 'average': 23, 'below_average': 19, 'poor': 15}
    }
}


class VO2MaxAnalysisService:
    """Service for comprehensive VO₂max analysis and insights generation."""

    @staticmethod
    def get_age_bracket(age: int) -> str:
        """Determine age bracket for benchmark comparison."""
        if age < 30:
            return '20-29'
        elif age < 40:
            return '30-39'
        elif age < 50:
            return '40-49'
        elif age < 60:
            return '50-59'
        elif age < 70:
            return '60-69'
        else:
            return '70+'

    @staticmethod
    def calculate_fitness_category(vo2_max: float, age: int, gender: str) -> Dict:
        """Calculate fitness category and percentile ranking."""
        try:
            age_bracket = VO2MaxAnalysisService.get_age_bracket(age)
            gender_key = gender.lower() if gender else 'male'
            
            if gender_key not in VO2_BENCHMARKS:
                gender_key = 'male'  # Default fallback
            
            benchmarks = VO2_BENCHMARKS[gender_key][age_bracket]
            
            # Determine category
            if vo2_max >= benchmarks['excellent']:
                category = 'Excellent'
                percentile = 90
            elif vo2_max >= benchmarks['good']:
                category = 'Good'
                percentile = 70
            elif vo2_max >= benchmarks['average']:
                category = 'Average'
                percentile = 50
            elif vo2_max >= benchmarks['below_average']:
                category = 'Below Average'
                percentile = 30
            else:
                category = 'Poor'
                percentile = 10
            
            # Calculate more precise percentile within category
            if category == 'Excellent':
                percentile = min(95, 90 + (vo2_max - benchmarks['excellent']) / 5)
            elif category == 'Good':
                range_size = benchmarks['excellent'] - benchmarks['good']
                percentile = 70 + ((vo2_max - benchmarks['good']) / range_size) * 20
            elif category == 'Average':
                range_size = benchmarks['good'] - benchmarks['average']
                percentile = 50 + ((vo2_max - benchmarks['average']) / range_size) * 20
            elif category == 'Below Average':
                range_size = benchmarks['average'] - benchmarks['below_average']
                percentile = 30 + ((vo2_max - benchmarks['below_average']) / range_size) * 20
            else:  # Poor
                percentile = max(5, 10 + (vo2_max - benchmarks['poor']) / 5)
            
            return {
                'category': category,
                'percentile': round(percentile, 1),
                'benchmarks': benchmarks,
                'age_bracket': age_bracket,
                'next_level': VO2MaxAnalysisService.get_next_level_target(vo2_max, benchmarks)
            }
            
        except Exception as e:
            logger.error(f"Error calculating fitness category: {e}")
            return {
                'category': 'Unknown',
                'percentile': 50,
                'benchmarks': {},
                'age_bracket': '',
                'next_level': None
            }

    @staticmethod
    def get_next_level_target(current_vo2: float, benchmarks: Dict) -> Optional[Dict]:
        """Calculate target for next fitness level."""
        levels = ['poor', 'below_average', 'average', 'good', 'excellent']
        
        for i, level in enumerate(levels):
            if current_vo2 < benchmarks[level]:
                return {
                    'target_level': level.replace('_', ' ').title(),
                    'target_vo2': benchmarks[level],
                    'improvement_needed': benchmarks[level] - current_vo2
                }
        
        # Already at excellent level
        return {
            'target_level': 'Elite',
            'target_vo2': benchmarks['excellent'] + 5,
            'improvement_needed': benchmarks['excellent'] + 5 - current_vo2
        }

    @staticmethod
    async def get_vo2_trend_analysis(
        db: AsyncSession, 
        user_id: str, 
        days_back: int = 90
    ) -> Dict:
        """Analyze VO₂max trends over specified timeframe."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Get VO₂max estimates
            query = select(VO2MaxEstimate).where(
                VO2MaxEstimate.user_id == user_id,
                VO2MaxEstimate.measured_at >= start_date
            ).order_by(VO2MaxEstimate.measured_at.asc())
            
            result = await db.execute(query)
            vo2_records = result.scalars().all()
            
            if len(vo2_records) < 2:
                return {
                    'trend_direction': 'insufficient_data',
                    'trend_strength': 0,
                    'improvement_rate': 0,
                    'volatility': 0,
                    'data_points': len(vo2_records)
                }
            
            # Prepare data for analysis
            dates = [(record.measured_at - start_date).days for record in vo2_records]
            values = [record.ml_per_kg_min for record in vo2_records]
            
            # Calculate trend using linear regression
            if len(dates) >= 2:
                X = np.array(dates).reshape(-1, 1)
                y = np.array(values)
                
                model = LinearRegression()
                model.fit(X, y)
                
                slope = model.coef_[0]
                r_squared = model.score(X, y)
                
                # Calculate monthly improvement rate
                monthly_rate = slope * 30  # slope per day * 30 days
                
                # Calculate volatility (standard deviation)
                volatility = stdev(values) if len(values) > 1 else 0
                
                # Determine trend direction
                if abs(slope) < 0.01:
                    trend_direction = 'stable'
                elif slope > 0:
                    trend_direction = 'improving'
                else:
                    trend_direction = 'declining'
                
                return {
                    'trend_direction': trend_direction,
                    'trend_strength': round(r_squared, 3),
                    'improvement_rate': round(monthly_rate, 2),
                    'volatility': round(volatility, 2),
                    'data_points': len(vo2_records),
                    'latest_value': values[-1],
                    'earliest_value': values[0],
                    'total_change': round(values[-1] - values[0], 2),
                    'total_change_percent': round(((values[-1] - values[0]) / values[0]) * 100, 1) if values[0] > 0 else 0
                }
            
        except Exception as e:
            logger.error(f"Error in VO₂ trend analysis: {e}")
            return {
                'trend_direction': 'error',
                'trend_strength': 0,
                'improvement_rate': 0,
                'volatility': 0,
                'data_points': 0
            }

    @staticmethod
    async def get_supporting_metrics(
        db: AsyncSession, 
        user_id: str, 
        days_back: int = 30
    ) -> Dict:
        """Get supporting cardiovascular health metrics."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Get average resting heart rate
            hr_query = select(HeartRateSample).where(
                HeartRateSample.user_id == user_id,
                HeartRateSample.captured_at >= start_date,
                HeartRateSample.context == 'resting'
            )
            hr_result = await db.execute(hr_query)
            hr_samples = hr_result.scalars().all()
            
            avg_resting_hr = mean([hr.bpm for hr in hr_samples]) if hr_samples else None
            
            # Get sleep quality metrics
            sleep_query = select(SleepSession).where(
                SleepSession.user_id == user_id,
                SleepSession.start_time >= start_date
            )
            sleep_result = await db.execute(sleep_query)
            sleep_sessions = sleep_result.scalars().all()
            
            avg_sleep_score = mean([session.score for session in sleep_sessions if session.score]) if sleep_sessions else None
            avg_sleep_duration = mean([session.duration_s / 3600 for session in sleep_sessions]) if sleep_sessions else None
            
            # Get daily step averages
            step_query = select(
                func.date(StepMinute.start_minute).label('date'),
                func.sum(StepMinute.steps).label('daily_steps')
            ).where(
                StepMinute.user_id == user_id,
                StepMinute.start_minute >= start_date
            ).group_by(func.date(StepMinute.start_minute))
            
            step_result = await db.execute(step_query)
            daily_steps = [row.daily_steps for row in step_result.fetchall()]
            avg_daily_steps = mean(daily_steps) if daily_steps else None
            
            return {
                'resting_heart_rate': {
                    'average': round(avg_resting_hr, 1) if avg_resting_hr else None,
                    'sample_count': len(hr_samples)
                },
                'sleep_metrics': {
                    'average_score': round(avg_sleep_score, 1) if avg_sleep_score else None,
                    'average_duration_hours': round(avg_sleep_duration, 1) if avg_sleep_duration else None,
                    'session_count': len(sleep_sessions)
                },
                'activity_metrics': {
                    'average_daily_steps': round(avg_daily_steps, 0) if avg_daily_steps else None,
                    'active_days': len(daily_steps)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting supporting metrics: {e}")
            return {
                'resting_heart_rate': {'average': None, 'sample_count': 0},
                'sleep_metrics': {'average_score': None, 'average_duration_hours': None, 'session_count': 0},
                'activity_metrics': {'average_daily_steps': None, 'active_days': 0}
            }

    @staticmethod
    def calculate_comprehensive_score(
        vo2_max: float,
        fitness_category: Dict,
        trend_analysis: Dict,
        supporting_metrics: Dict
    ) -> Dict:
        """Calculate comprehensive cardiovascular fitness score (0-100)."""
        try:
            # Component scores
            scores = {}
            
            # 1. VO₂max Score (40% weight) - based on percentile
            scores['vo2_score'] = fitness_category['percentile']
            
            # 2. Trend Score (25% weight)
            trend_score = 50  # Baseline
            if trend_analysis['trend_direction'] == 'improving':
                trend_score = min(90, 50 + (trend_analysis['improvement_rate'] * 10))
            elif trend_analysis['trend_direction'] == 'declining':
                trend_score = max(10, 50 + (trend_analysis['improvement_rate'] * 10))
            scores['trend_score'] = trend_score
            
            # 3. Consistency Score (15% weight) - based on data availability
            data_points = trend_analysis['data_points']
            if data_points >= 10:
                consistency_score = 90
            elif data_points >= 5:
                consistency_score = 70
            elif data_points >= 2:
                consistency_score = 50
            else:
                consistency_score = 20
            scores['consistency_score'] = consistency_score
            
            # 4. Recovery Score (10% weight) - based on resting HR and sleep
            recovery_score = 50
            rhr = supporting_metrics['resting_heart_rate']['average']
            sleep_score = supporting_metrics['sleep_metrics']['average_score']
            
            if rhr and rhr < 60:  # Good resting HR
                recovery_score += 20
            elif rhr and rhr > 80:  # High resting HR
                recovery_score -= 20
                
            if sleep_score and sleep_score > 80:  # Good sleep
                recovery_score += 15
            elif sleep_score and sleep_score < 60:  # Poor sleep
                recovery_score -= 15
                
            scores['recovery_score'] = max(0, min(100, recovery_score))
            
            # 5. Activity Score (10% weight) - based on steps
            activity_score = 50
            steps = supporting_metrics['activity_metrics']['average_daily_steps']
            if steps:
                if steps > 10000:
                    activity_score = 90
                elif steps > 7500:
                    activity_score = 75
                elif steps > 5000:
                    activity_score = 60
                elif steps < 3000:
                    activity_score = 25
            scores['activity_score'] = activity_score
            
            # Calculate weighted total
            weights = {
                'vo2_score': 0.40,
                'trend_score': 0.25,
                'consistency_score': 0.15,
                'recovery_score': 0.10,
                'activity_score': 0.10
            }
            
            total_score = sum(scores[component] * weights[component] for component in scores)
            
            return {
                'total_score': round(total_score, 1),
                'component_scores': {k: round(v, 1) for k, v in scores.items()},
                'weights': weights,
                'grade': VO2MaxAnalysisService.get_score_grade(total_score)
            }
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive score: {e}")
            return {
                'total_score': 50,
                'component_scores': {},
                'weights': {},
                'grade': 'C'
            }

    @staticmethod
    def get_score_grade(score: float) -> str:
        """Convert numerical score to letter grade."""
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'A-'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 65:
            return 'B-'
        elif score >= 60:
            return 'C+'
        elif score >= 55:
            return 'C'
        elif score >= 50:
            return 'C-'
        elif score >= 40:
            return 'D'
        else:
            return 'F'

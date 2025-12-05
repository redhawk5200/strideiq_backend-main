"""
Progress Controller
"""
from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Dict, List

from app.models.coaching_recommendation import CoachingRecommendation
from app.models.vo2_max_estimate import VO2MaxEstimate
from app.models.workout_session import WorkoutSession
from app.models.user_injury import UserInjury
from app.schemas.progress_schemas import (
    ProgressResponse, WeeklyStats, VO2Trend,
    WorkoutSummary, InjurySummary
)
from app.core.logger import get_logger

logger = get_logger("progress_controller")


class ProgressController:
    """Controller for user progress data."""

    @staticmethod
    async def get_progress(request: Request, db: AsyncSession) -> Dict:
        """Get comprehensive progress data for user."""

        try:
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user_id = request.state.user.id
            today = datetime.utcnow().date()

            # Calculate current week (last 7 days)
            current_week = await ProgressController._get_week_stats(
                db, user_id, today - timedelta(days=6), today
            )

            # Calculate last 4 weeks
            last_4_weeks = []
            for i in range(4):
                week_end = today - timedelta(days=7 * i)
                week_start = week_end - timedelta(days=6)
                week_stats = await ProgressController._get_week_stats(
                    db, user_id, week_start, week_end
                )
                last_4_weeks.append(week_stats)

            # VO2 trend (last 30 days)
            vo2_trend = await ProgressController._get_vo2_trend(db, user_id, 30)

            # Recent workouts (last 7 days)
            recent_workouts = await ProgressController._get_recent_workouts(
                db, user_id, 7
            )

            # Active injuries
            active_injuries = await ProgressController._get_active_injuries(
                db, user_id
            )

            # Personal records
            longest_run = await ProgressController._get_longest_run(db, user_id)
            best_vo2 = await ProgressController._get_best_vo2(db, user_id)
            total_workouts = await ProgressController._get_total_workouts(db, user_id)

            # Current streak
            streak = await ProgressController._get_current_streak(db, user_id)

            return ProgressResponse(
                current_week=current_week,
                last_4_weeks=last_4_weeks,
                vo2_trend=vo2_trend,
                recent_workouts=recent_workouts,
                active_injuries=active_injuries,
                longest_run_miles=longest_run,
                best_vo2_max=best_vo2,
                total_workouts_all_time=total_workouts,
                current_streak_days=streak
            ).dict()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error getting progress: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @staticmethod
    async def _get_week_stats(
        db: AsyncSession, user_id: str, start_date, end_date
    ) -> WeeklyStats:
        """Get stats for a specific week."""

        # Get all plans for the week
        result = await db.execute(
            select(CoachingRecommendation)
            .where(CoachingRecommendation.user_id == user_id)
            .where(func.date(CoachingRecommendation.recommendation_date) >= start_date)
            .where(func.date(CoachingRecommendation.recommendation_date) <= end_date)
        )
        plans = result.scalars().all()

        total = len(plans)
        completed = sum(1 for p in plans if p.status == 'completed')
        compliance = (completed / total * 100) if total > 0 else 0

        # Get workout sessions for the week
        workout_result = await db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .where(func.date(WorkoutSession.start_time) >= start_date)
            .where(func.date(WorkoutSession.start_time) <= end_date)
        )
        workouts = workout_result.scalars().all()

        total_distance = sum(w.distance_miles or 0 for w in workouts)
        total_duration = sum(w.duration_seconds or 0 for w in workouts) // 60

        # Average heart rate
        hr_values = [w.avg_heart_rate for w in workouts if w.avg_heart_rate]
        avg_hr = int(sum(hr_values) / len(hr_values)) if hr_values else None

        return WeeklyStats(
            total_workouts=total,
            completed_workouts=completed,
            compliance_rate=round(compliance, 1),
            total_distance_miles=round(total_distance, 2),
            total_duration_minutes=total_duration,
            avg_heart_rate=avg_hr
        )

    @staticmethod
    async def _get_vo2_trend(
        db: AsyncSession, user_id: str, days: int
    ) -> List[VO2Trend]:
        """Get VO2 max trend for last N days (excludes manually entered data)."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(VO2MaxEstimate)
            .where(VO2MaxEstimate.user_id == user_id)
            .where(VO2MaxEstimate.measured_at >= cutoff)
            .where(VO2MaxEstimate.device_id.isnot(None))  # Only device-tracked data
            .order_by(VO2MaxEstimate.measured_at)
        )
        estimates = result.scalars().all()

        return [
            VO2Trend(
                date=e.measured_at.date(),
                vo2_max=round(e.ml_per_kg_min, 1)
            )
            for e in estimates
        ]

    @staticmethod
    async def _get_recent_workouts(
        db: AsyncSession, user_id: str, days: int
    ) -> List[WorkoutSummary]:
        """Get recent workout summaries."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(CoachingRecommendation)
            .where(CoachingRecommendation.user_id == user_id)
            .where(CoachingRecommendation.recommendation_date >= cutoff)
            .order_by(desc(CoachingRecommendation.recommendation_date))
        )
        plans = result.scalars().all()

        workouts = []
        for plan in plans:
            distance = None
            plan_date = plan.recommendation_date.date()

            if plan.workout_type in ['run', 'walk', 'cycling']:
                # Try to get actual distance from workout session
                workout_result = await db.execute(
                    select(WorkoutSession)
                    .where(WorkoutSession.user_id == user_id)
                    .where(func.date(WorkoutSession.start_time) == plan_date)
                    .limit(1)
                )
                workout = workout_result.scalar_one_or_none()
                if workout and workout.distance_miles:
                    distance = round(workout.distance_miles, 2)

            workouts.append(WorkoutSummary(
                date=plan_date,
                workout_type=plan.workout_type or 'unknown',
                duration_minutes=plan.duration_minutes or 0,
                distance_miles=distance,
                status=plan.status
            ))

        return workouts

    @staticmethod
    async def _get_active_injuries(
        db: AsyncSession, user_id: str
    ) -> List[InjurySummary]:
        """Get active injuries."""

        result = await db.execute(
            select(UserInjury)
            .where(UserInjury.user_id == user_id)
            .where(UserInjury.status.in_(['active', 'recovering']))
            .order_by(desc(UserInjury.injury_date))
        )
        injuries = result.scalars().all()

        return [
            InjurySummary(
                injury_type=inj.injury_type,
                affected_area=inj.affected_area,
                pain_level=inj.current_pain_level or inj.initial_pain_level,
                days_since_injury=(datetime.utcnow().date() - inj.injury_date.date()).days,
                status=inj.status
            )
            for inj in injuries
        ]

    @staticmethod
    async def _get_longest_run(db: AsyncSession, user_id: str) -> float:
        """Get longest run ever."""

        result = await db.execute(
            select(func.max(WorkoutSession.distance_miles))
            .where(WorkoutSession.user_id == user_id)
            .where(WorkoutSession.activity_type.in_(['running', 'run']))
        )
        max_distance = result.scalar()

        return round(max_distance, 2) if max_distance else 0.0

    @staticmethod
    async def _get_best_vo2(db: AsyncSession, user_id: str) -> float:
        """Get best VO2 max (excludes manually entered data)."""

        result = await db.execute(
            select(func.max(VO2MaxEstimate.ml_per_kg_min))
            .where(VO2MaxEstimate.user_id == user_id)
            .where(VO2MaxEstimate.device_id.isnot(None))  # Only device-tracked data
        )
        max_vo2 = result.scalar()

        return round(max_vo2, 1) if max_vo2 else None

    @staticmethod
    async def _get_total_workouts(db: AsyncSession, user_id: str) -> int:
        """Get total completed workouts all time."""

        result = await db.execute(
            select(func.count(CoachingRecommendation.id))
            .where(CoachingRecommendation.user_id == user_id)
            .where(CoachingRecommendation.status == 'completed')
        )

        return result.scalar() or 0

    @staticmethod
    async def _get_current_streak(db: AsyncSession, user_id: str) -> int:
        """Calculate current workout streak in days."""

        result = await db.execute(
            select(CoachingRecommendation)
            .where(CoachingRecommendation.user_id == user_id)
            .where(CoachingRecommendation.status == 'completed')
            .order_by(desc(CoachingRecommendation.recommendation_date))
            .limit(30)
        )
        workouts = result.scalars().all()

        if not workouts:
            return 0

        # Count consecutive days
        streak = 0
        current_date = datetime.utcnow().date()

        for workout in workouts:
            workout_date = workout.recommendation_date.date()
            if workout_date == current_date - timedelta(days=streak):
                streak += 1
            else:
                break

        return streak

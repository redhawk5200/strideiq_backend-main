"""
Progress API Schemas
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class WeeklyStats(BaseModel):
    """Weekly training statistics"""
    total_workouts: int
    completed_workouts: int
    compliance_rate: float  # percentage
    total_distance_miles: float
    total_duration_minutes: int
    avg_heart_rate: Optional[int]


class VO2Trend(BaseModel):
    """VO2 max trend data"""
    date: date
    vo2_max: float


class WorkoutSummary(BaseModel):
    """Recent workout summary"""
    date: date
    workout_type: str
    duration_minutes: int
    distance_miles: Optional[float]
    status: str  # completed, skipped, partial


class InjurySummary(BaseModel):
    """Active injury summary"""
    injury_type: str
    affected_area: str
    pain_level: int
    days_since_injury: int
    status: str


class ProgressResponse(BaseModel):
    """Complete progress data"""
    # This week stats
    current_week: WeeklyStats

    # Last 4 weeks stats
    last_4_weeks: List[WeeklyStats]

    # VO2 max trend (last 30 days)
    vo2_trend: List[VO2Trend]

    # Recent workouts (last 7 days)
    recent_workouts: List[WorkoutSummary]

    # Active injuries
    active_injuries: List[InjurySummary]

    # Personal records
    longest_run_miles: Optional[float]
    best_vo2_max: Optional[float]
    total_workouts_all_time: int

    # Current streak
    current_streak_days: int

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class HeartRateInputSchema(BaseModel):
    """Schema for heart rate data input"""
    captured_at: datetime = Field(..., description="When the heart rate was captured (UTC)")
    bpm: int = Field(..., ge=30, le=250, description="Beats per minute")
    context: Optional[str] = Field(None, description="Context: 'resting', 'workout', 'sleep', 'unknown'")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence level (0-1)")
    quality: Optional[str] = Field(None, description="Quality: 'good', 'questionable', 'bad'")
    flags: Optional[Dict[str, Any]] = Field(None, description="Additional flags/metadata")
    
    @validator('captured_at')
    def convert_to_naive_utc(cls, v):
        """Convert timezone-aware datetime to naive UTC for database storage"""
        if v.tzinfo is not None:
            # Convert to UTC and make naive
            import pytz
            utc_dt = v.astimezone(pytz.UTC)
            return utc_dt.replace(tzinfo=None)
        return v
    
    @validator('context')
    def validate_context(cls, v):
        if v is not None:
            allowed_contexts = ['resting', 'workout', 'sleep', 'unknown']
            if v not in allowed_contexts:
                raise ValueError(f"Context must be one of: {allowed_contexts}")
        return v
    
    @validator('quality')
    def validate_quality(cls, v):
        if v is not None:
            allowed_qualities = ['good', 'questionable', 'bad']
            if v not in allowed_qualities:
                raise ValueError(f"Quality must be one of: {allowed_qualities}")
        return v


class SleepSessionInputSchema(BaseModel):
    """Schema for sleep session data input"""
    start_time: datetime = Field(..., description="Sleep start time (UTC)")
    end_time: datetime = Field(..., description="Sleep end time (UTC)")
    score: Optional[int] = Field(None, ge=0, le=100, description="Sleep score (0-100)")
    latency_s: Optional[int] = Field(None, ge=0, description="Time to fall asleep in seconds")
    awakenings: Optional[int] = Field(None, ge=0, description="Number of awakenings")
    efficiency_pct: Optional[int] = Field(None, ge=0, le=100, description="Sleep efficiency percentage")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Additional sleep metrics")
    
    @validator('start_time', 'end_time')
    def convert_to_naive_utc(cls, v):
        """Convert timezone-aware datetime to naive UTC for database storage"""
        if v.tzinfo is not None:
            import pytz
            utc_dt = v.astimezone(pytz.UTC)
            return utc_dt.replace(tzinfo=None)
        return v


class StepDataInputSchema(BaseModel):
    """Schema for step count data input"""
    start_minute: datetime = Field(..., description="Start minute for step count (UTC)")
    steps: int = Field(..., ge=0, description="Number of steps in this minute")
    
    @validator('start_minute')
    def convert_to_naive_utc(cls, v):
        """Convert timezone-aware datetime to naive UTC for database storage"""
        if v.tzinfo is not None:
            import pytz
            utc_dt = v.astimezone(pytz.UTC)
            return utc_dt.replace(tzinfo=None)
        return v


class VO2MaxInputSchema(BaseModel):
    """Schema for VO2 max data input"""
    measured_at: datetime = Field(..., description="When the measurement was taken (UTC)")
    ml_per_kg_min: float = Field(..., ge=10, le=90, description="VO2 max value in mL·kg⁻¹·min⁻¹")
    estimation_method: str = Field(..., description="Method used: 'apple_health', 'fitbit_cardio_fitness', 'lab', 'field_test'")
    context: Optional[str] = Field(None, description="Activity context: 'running', 'walking', etc.")
    
    @validator('measured_at')
    def convert_to_naive_utc(cls, v):
        """Convert timezone-aware datetime to naive UTC for database storage"""
        if v.tzinfo is not None:
            import pytz
            utc_dt = v.astimezone(pytz.UTC)
            return utc_dt.replace(tzinfo=None)
        return v


class BulkHealthDataInputSchema(BaseModel):
    """Schema for bulk health data input"""
    heart_rate_samples: Optional[List[HeartRateInputSchema]] = Field(None, description="Heart rate data")
    sleep_sessions: Optional[List[SleepSessionInputSchema]] = Field(None, description="Sleep session data")
    step_data: Optional[List[StepDataInputSchema]] = Field(None, description="Step count data")
    vo2_max_estimates: Optional[List[VO2MaxInputSchema]] = Field(None, description="VO2 max data")


class HealthDataResponse(BaseModel):
    """Response schema for health data operations"""
    success: bool
    message: str
    inserted_count: int
    errors: Optional[List[str]] = None

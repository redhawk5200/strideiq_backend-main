from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime

from app.enums import (
    Gender,
    UnitPreference,
    GoalType,
    GoalPriority,
    TrainingLevel,
    TimeWindow,
    WorkoutType,
    OnboardingStep
)


# Request schemas
class UserProfileCreate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[Gender] = None
    birth_date: Optional[str] = Field(None, description="Birth date in MM/DD/YYYY format")
    height_inches: Optional[float] = Field(None, gt=0, le=300, description="Height in inches (up to 25 feet)")
    unit_preference: UnitPreference = UnitPreference.IMPERIAL

    @validator('birth_date')
    def validate_birth_date(cls, v):
        if v is None:
            return None
        try:
            # Parse American format MM/DD/YYYY
            parsed_date = datetime.strptime(v, "%m/%d/%Y").date()
            
            # Validate reasonable age range (10-120 years old)
            today = date.today()
            age = today.year - parsed_date.year - ((today.month, today.day) < (parsed_date.month, parsed_date.day))
            
            if age < 10 or age > 120:
                raise ValueError('Age must be between 10 and 120 years')
            
            return parsed_date
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError('Birth date must be in MM/DD/YYYY format (e.g., 05/15/1990)')
            raise e

    @validator('height_inches')
    def validate_height(cls, v):
        if v is not None and (v < 20 or v > 300):
            raise ValueError('Height must be between 20 and 300 inches (1.7 to 25 feet)')
        return v


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[Gender] = None
    birth_date: Optional[str] = Field(None, description="Birth date in MM/DD/YYYY format")
    height_inches: Optional[float] = Field(None, gt=0, le=300, description="Height in inches (up to 25 feet)")
    unit_preference: Optional[UnitPreference] = None

    @validator('birth_date')
    def validate_birth_date(cls, v):
        if v is None:
            return None
        try:
            # Parse American format MM/DD/YYYY
            parsed_date = datetime.strptime(v, "%m/%d/%Y").date()
            
            # Validate reasonable age range (10-120 years old)
            today = date.today()
            age = today.year - parsed_date.year - ((today.month, today.day) < (parsed_date.month, parsed_date.day))
            
            if age < 10 or age > 120:
                raise ValueError('Age must be between 10 and 120 years')
            
            return parsed_date
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError('Birth date must be in MM/DD/YYYY format (e.g., 05/15/1990)')
            raise e

    @validator('height_inches')
    def validate_height(cls, v):
        if v is not None and (v < 20 or v > 300):
            raise ValueError('Height must be between 20 and 300 inches (1.7 to 25 feet)')
        return v


class UserGoalCreate(BaseModel):
    goal_type: GoalType
    description: Optional[str] = None
    target_value: Optional[str] = None
    target_date: Optional[str] = Field(None, description="Target date in MM/DD/YYYY format")
    priority: GoalPriority = GoalPriority.MEDIUM

    @validator('target_date')
    def validate_target_date(cls, v):
        if v is None:
            return None
        try:
            # Parse American format MM/DD/YYYY
            parsed_date = datetime.strptime(v, "%m/%d/%Y").date()
            
            # Validate that target date is not in the past
            today = date.today()
            if parsed_date < today:
                raise ValueError('Target date cannot be in the past')
            
            return parsed_date
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError('Target date must be in MM/DD/YYYY format (e.g., 12/31/2025)')
            raise e


class TrainingPreferencesCreate(BaseModel):
    training_level: TrainingLevel
    sessions_per_day: int = Field(1, ge=1, le=5)
    days_per_week: int = Field(3, ge=1, le=7)
    preferred_time_window: Optional[TimeWindow] = None

    @validator('sessions_per_day')
    def validate_sessions_per_day(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Sessions per day must be between 1 and 5')
        return v

    @validator('days_per_week')
    def validate_days_per_week(cls, v):
        if v < 1 or v > 7:
            raise ValueError('Days per week must be between 1 and 7')
        return v


class WorkoutPreferenceCreate(BaseModel):
    workout_type: WorkoutType
    rank: Optional[int] = Field(None, ge=1, le=20)


class WorkoutPreferencesCreate(BaseModel):
    preferences: List[WorkoutPreferenceCreate] = Field(..., min_items=1, max_items=10)

    @validator('preferences')
    def validate_unique_workout_types(cls, v):
        workout_types = [pref.workout_type for pref in v]
        if len(workout_types) != len(set(workout_types)):
            raise ValueError('Duplicate workout types are not allowed')
        return v


class UserConsentCreate(BaseModel):
    consent_type: str
    granted: bool
    version: str = "1.0"


class BodyWeightCreate(BaseModel):
    weight_lbs: str = Field(..., pattern=r'^\d+(\.\d{1,2})?$')
    notes: Optional[str] = None

    @validator('weight_lbs')
    def validate_weight(cls, v):
        try:
            weight = float(v)
            if weight < 30 or weight > 1000:
                raise ValueError('Weight must be between 30 and 1000 lbs')
            return v
        except ValueError as e:
            if "Weight must be between" in str(e):
                raise e  # Re-raise the weight range error with proper message
            raise ValueError('Invalid weight format')


class TargetWeightCreate(BaseModel):
    target_weight_lbs: str = Field(..., pattern=r'^\d+(\.\d{1,2})?$')
    goal_type: str = Field(..., pattern="^(weight_loss|weight_gain)$")
    target_date: Optional[str] = None  # Optional target date in MM/DD/YYYY format
    description: Optional[str] = None

    @validator('target_weight_lbs')
    def validate_target_weight(cls, v):
        try:
            weight = float(v)
            if weight < 30 or weight > 1000:
                raise ValueError('Target weight must be between 30 and 1000 lbs')
            return v
        except ValueError as e:
            if "Target weight must be between" in str(e):
                raise e  # Re-raise the weight range error with proper message
            raise ValueError('Invalid target weight format')


class MainTargetCreate(BaseModel):
    """Schema for user's main fitness target selection."""
    main_target: str = Field(..., pattern="^(vo2_max|race_time)$", description="User's primary fitness goal")

    class Config:
        schema_extra = {
            "example": {
                "main_target": "vo2_max"
            }
        }


class FitnessDataCreate(BaseModel):
    """Schema for saving user's current fitness baseline (VO2 Max and Race Time)."""
    vo2_max: float = Field(..., gt=0, le=150, description="VO2 Max in ml/kg/min (typically 20-90, max 150)")
    race_time: float = Field(..., gt=0, le=500, description="Most recent race time in minutes (max 500 for ultra races)")

    class Config:
        schema_extra = {
            "example": {
                "vo2_max": 45.5,
                "race_time": 25.3
            }
        }


class MedicalConditionResponse(BaseModel):
    """Response schema for medical condition."""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    display_order: int = 0

    class Config:
        from_attributes = True


class UserMedicalConditionsCreate(BaseModel):
    """Schema for saving user's selected medical conditions."""
    condition_ids: List[str] = Field(..., description="List of medical condition IDs")

    class Config:
        schema_extra = {
            "example": {
                "condition_ids": ["med_002", "med_006"]
            }
        }


class FitnessStatusCreate(BaseModel):
    """Schema for saving user's fitness status level."""
    fitness_status: str = Field(..., pattern="^(beginner|intermediate|advanced)$", description="User's fitness level")

    class Config:
        schema_extra = {
            "example": {
                "fitness_status": "intermediate"
            }
        }


class UserMoodCreate(BaseModel):
    """Schema for saving user's current mood."""
    mood: str = Field(..., pattern="^(normal|happy|energetic|nervous|sad|tired|angry)$", description="User's current mood")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes about the mood")

    class Config:
        schema_extra = {
            "example": {
                "mood": "happy",
                "notes": "Feeling great after morning workout"
            }
        }


class DailyTrainingIntentionCreate(BaseModel):
    """Schema for saving user's daily training intention."""
    intention: str = Field(..., pattern="^(yes|no|maybe)$", description="User's intention to train today")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes about the training intention")

    class Config:
        schema_extra = {
            "example": {
                "intention": "yes",
                "notes": "Ready to train today"
            }
        }


class WeightDataCreate(BaseModel):
    """Combined schema for saving both current and target weight."""
    current_weight_lbs: str = Field(..., pattern=r'^\d+(\.\d{1,2})?$')
    target_weight_lbs: str = Field(..., pattern=r'^\d+(\.\d{1,2})?$')
    goal_type: Optional[str] = Field(None, pattern="^(weight_loss|weight_gain|maintain)$")
    target_date: Optional[str] = None  # Optional target date in MM/DD/YYYY format
    notes: Optional[str] = None

    @validator('current_weight_lbs')
    def validate_current_weight(cls, v):
        try:
            weight = float(v)
            if weight < 30 or weight > 1000:
                raise ValueError('Current weight must be between 30 and 1000 lbs')
            return v
        except ValueError as e:
            if "Current weight must be between" in str(e):
                raise e
            raise ValueError('Invalid current weight format')

    @validator('target_weight_lbs')
    def validate_target_weight(cls, v):
        try:
            weight = float(v)
            if weight < 30 or weight > 1000:
                raise ValueError('Target weight must be between 30 and 1000 lbs')
            return v
        except ValueError as e:
            if "Target weight must be between" in str(e):
                raise e
            raise ValueError('Invalid target weight format')

    @validator('goal_type', always=True)
    def determine_goal_type(cls, v, values):
        """Auto-determine goal type based on current vs target weight if not provided."""
        if v is not None:
            return v

        if 'current_weight_lbs' in values and 'target_weight_lbs' in values:
            current = float(values['current_weight_lbs'])
            target = float(values['target_weight_lbs'])

            if target < current:
                return 'weight_loss'
            elif target > current:
                return 'weight_gain'
            else:
                return 'maintain'

        return 'maintain'  # default


# Response schemas
class UserProfileResponse(BaseModel):
    id: str
    user_id: str
    first_name: Optional[str]
    last_name: Optional[str]
    gender: Optional[str]
    birth_date: Optional[str]  # Keep as string in MM/DD/YYYY format
    height_inches: Optional[float]
    unit_preference: str
    age: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserGoalResponse(BaseModel):
    id: str
    profile_id: str
    goal_type: str
    description: Optional[str]
    target_value: Optional[str]
    target_date: Optional[date]
    priority: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TrainingPreferencesResponse(BaseModel):
    id: str
    profile_id: str
    training_level: str
    sessions_per_day: int
    days_per_week: int
    preferred_time_window: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkoutPreferenceResponse(BaseModel):
    id: str
    profile_id: str
    workout_type: str
    rank: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class OnboardingProgressResponse(BaseModel):
    id: str
    profile_id: str
    current_step: str
    completed_steps: str
    current_frontend_step: Optional[str] = None
    is_completed: bool
    started_at: datetime
    completed_at: Optional[datetime]
    updated_at: datetime

    @validator('current_step', pre=True)
    def serialize_current_step(cls, v):
        if hasattr(v, 'value'):  # It's an enum
            return v.value
        return v

    class Config:
        from_attributes = True


class UserConsentResponse(BaseModel):
    id: str
    profile_id: str
    consent_type: str
    granted: bool
    version: str
    granted_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


class BodyWeightResponse(BaseModel):
    id: str
    user_id: str
    weight_lbs: float = Field(alias="value_lbs")
    measured_at: datetime
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class TargetWeightResponse(BaseModel):
    id: str
    profile_id: str
    target_weight_lbs: float
    goal_type: str
    target_date: Optional[date]
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class OnboardingStatusResponse(BaseModel):
    profile: UserProfileResponse
    onboarding_progress: Optional[OnboardingProgressResponse]
    goals: List[UserGoalResponse]
    training_preferences: Optional[TrainingPreferencesResponse]
    workout_preferences: List[WorkoutPreferenceResponse]
    latest_weight: Optional[BodyWeightResponse]
    current_weight_lbs: Optional[float]
    target_weight_lbs: Optional[float]
    weight_goal_type: Optional[str]

    class Config:
        from_attributes = True


class OnboardingProgressUpdate(BaseModel):
    current_step: str = Field(..., description="Current onboarding step (e.g., 'basic_info', 'goals', 'weight')")
    current_frontend_step: Optional[str] = Field(None, description="Frontend screen name or step number for precise resume")

    @validator('current_step')
    def validate_current_step(cls, v):
        valid_steps = ['basic_info', 'goals', 'weight', 'training_preferences', 'workout_preferences', 'health_metrics', 'completed']
        if v not in valid_steps:
            raise ValueError(f'Invalid step. Must be one of: {", ".join(valid_steps)}')
        return v

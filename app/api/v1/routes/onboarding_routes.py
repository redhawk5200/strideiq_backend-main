from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.connection import get_db
from app.middlewares.clerk_auth import get_authenticated_user
from app.api.v1.controllers.onboarding_controller import OnboardingController
from app.models.user import User
from app.schemas.onboarding_schemas import (
    UserProfileCreate, UserProfileUpdate, UserGoalCreate,
    TrainingPreferencesCreate, WorkoutPreferencesCreate,
    UserConsentCreate, BodyWeightCreate, TargetWeightCreate, WeightDataCreate, MainTargetCreate, FitnessDataCreate,
    UserMedicalConditionsCreate, FitnessStatusCreate, UserMoodCreate, DailyTrainingIntentionCreate,
    OnboardingProgressUpdate,
    UserProfileResponse, UserGoalResponse, TrainingPreferencesResponse,
    WorkoutPreferenceResponse, OnboardingProgressResponse,
    UserConsentResponse, BodyWeightResponse, OnboardingStatusResponse
)
from app.core.logger import get_logger
import os

logger = get_logger("onboarding_routes")

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

# Development mode detection
IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "development") == "development"

# Add a simple health check for onboarding
@router.get(
    "/health",
    summary="Health Check",
    description="Simple health check for onboarding service. No authentication required."
)
async def onboarding_health():
    """Health check for onboarding endpoints."""
    return {
        "status": "healthy", 
        "service": "onboarding",
        "development_mode": IS_DEVELOPMENT,
        "message": "Onboarding service is running"
    }


@router.get(
    "/status", 
    response_model=OnboardingStatusResponse,
    summary="Get Onboarding Status",
    description="Get complete onboarding status including profile, goals, and preferences." + 
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def get_onboarding_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Get complete onboarding status for the current user."""
    return await OnboardingController.get_onboarding_status(db, user.id)


@router.get(
    "/profile", 
    response_model=UserProfileResponse,
    summary="Get User Profile",
    description="Get current user profile data." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def get_user_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Get current user profile."""
    return await OnboardingController.get_user_profile(db, user.id)


@router.put(
    "/profile", 
    response_model=UserProfileResponse,
    summary="Update User Profile",
    description="Update existing user profile with new data." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def update_user_profile(
    request: Request,
    profile_data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Update existing user profile."""
    logger.info(f"PUT /profile - User: {user.email if user else 'None'}, Data: {profile_data}")
    return await OnboardingController.create_or_update_profile(
        db, user.id, profile_data
    )


@router.post(
    "/profile", 
    response_model=UserProfileResponse,
    summary="Create User Profile",
    description="Create or update user profile (upsert operation)." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def create_user_profile(
    request: Request,
    profile_data: UserProfileCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Create or update user profile (upsert operation)."""
    logger.info(f"POST /profile - User: {user.email if user else 'None'}, Data: {profile_data}")
    return await OnboardingController.create_or_update_profile(
        db, user.id, profile_data
    )


@router.post(
    "/input/goals",
    response_model=List[UserGoalResponse],
    summary="Create Goals",
    description="Create user fitness goals." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def create_goals(
    goals_data: List[UserGoalCreate],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Create user fitness goals."""
    return await OnboardingController.create_goals(db, user.id, goals_data)


@router.post(
    "/input/main-target",
    response_model=dict,
    summary="Save Main Fitness Target",
    description="Save user's main fitness target (VO2 Max or Race Time)." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def save_main_target(
    target_data: MainTargetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Save user's main fitness target selection."""
    return await OnboardingController.save_main_target(db, user.id, target_data)


@router.post(
    "/input/fitness-data",
    response_model=dict,
    summary="Save Fitness Baseline Data",
    description="Save user's current fitness baseline (VO2 Max and Race Time)." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def save_fitness_data(
    fitness_data: FitnessDataCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Save user's current fitness baseline."""
    return await OnboardingController.save_fitness_data(db, user.id, fitness_data)


@router.get(
    "/medical-conditions",
    response_model=List[dict],
    summary="Get Medical Conditions",
    description="Get all available medical conditions for user selection." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def get_medical_conditions(
    db: AsyncSession = Depends(get_db)
):
    """Get all active medical conditions."""
    return await OnboardingController.get_medical_conditions(db)


@router.post(
    "/input/medical-conditions",
    response_model=dict,
    summary="Save User Medical Conditions",
    description="Save user's selected medical conditions." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def save_user_medical_conditions(
    conditions_data: UserMedicalConditionsCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Save user's selected medical conditions."""
    return await OnboardingController.save_user_medical_conditions(db, user.id, conditions_data)


@router.post(
    "/input/fitness-status",
    response_model=dict,
    summary="Save User Fitness Status",
    description="Save user's fitness status level (beginner/intermediate/advanced)." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def save_fitness_status(
    status_data: FitnessStatusCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Save user's fitness status level."""
    return await OnboardingController.save_fitness_status(db, user.id, status_data)


@router.post(
    "/input/mood",
    response_model=dict,
    summary="Save User Mood",
    description="Save user's current mood during onboarding." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def save_user_mood(
    mood_data: UserMoodCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Save user's current mood."""
    return await OnboardingController.save_user_mood(db, user.id, mood_data)


@router.post(
    "/input/training-intention",
    response_model=dict,
    summary="Save Daily Training Intention",
    description="Save user's daily training intention (Yes/No/Maybe for training today)." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def save_daily_training_intention(
    intention_data: DailyTrainingIntentionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Save user's daily training intention."""
    return await OnboardingController.save_daily_training_intention(db, user.id, intention_data)


@router.post(
    "/input/training-preferences", 
    response_model=TrainingPreferencesResponse,
    summary="Create Training Preferences",
    description="Create user training preferences including medical conditions." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def create_training_preferences(
    preferences_data: TrainingPreferencesCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Create user training preferences."""
    return await OnboardingController.create_training_preferences(
        db, user.id, preferences_data
    )


@router.post(
    "/input/workout-preferences", 
    response_model=List[WorkoutPreferenceResponse],
    summary="Create Workout Preferences",
    description="Create user workout preferences and activity types." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def create_workout_preferences(
    preferences_data: WorkoutPreferencesCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Create user workout preferences."""
    return await OnboardingController.create_workout_preferences(
        db, user.id, preferences_data
    )


@router.post(
    "/input/weight/current", 
    response_model=BodyWeightResponse,
    summary="Set Current Weight",
    description="Set user's current weight measurement." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def set_current_weight(
    weight_data: BodyWeightCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Set user's current weight measurement."""
    return await OnboardingController.add_weight_measurement(
        db, user.id, weight_data
    )


@router.post(
    "/input/weight/target",
    response_model=dict,
    summary="Set Target Weight",
    description="Set user's target weight goal." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def set_target_weight(
    target_data: TargetWeightCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Set user's target weight goal."""
    return await OnboardingController.set_target_weight(
        db, user.id, target_data
    )


@router.post(
    "/input/weight",
    response_model=dict,
    summary="Save Weight Data",
    description="Save both current weight and target weight in a single call." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def save_weight_data(
    weight_data: WeightDataCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Save both current and target weight measurements."""
    return await OnboardingController.save_weight_data(
        db, user.id, weight_data
    )


@router.post(
    "/input/consent", 
    response_model=UserConsentResponse,
    summary="Create Consent",
    description="Create user consent record for data usage." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def create_consent(
    consent_data: UserConsentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Create user consent record."""
    return await OnboardingController.create_consent(db, user.id, consent_data)


@router.post(
    "/complete", 
    response_model=OnboardingProgressResponse,
    summary="Complete Onboarding",
    description="Mark onboarding process as completed." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def complete_onboarding(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Mark onboarding as completed."""
    return await OnboardingController.complete_onboarding(db, user.id)


@router.get(
    "/input/weight/current", 
    response_model=dict,
    summary="Get Current Weight",
    description="Get the user's most recent weight measurement." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def get_current_weight(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Get the user's most recent weight measurement."""
    return await OnboardingController.get_current_weight(db, user.id)


@router.get(
    "/input/weight/target",
    response_model=dict,
    summary="Get Target Weight",
    description="Get the user's target weight from their weight-related goals." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def get_target_weight(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Get the user's target weight from their weight-related goals."""
    return await OnboardingController.get_target_weight(db, user.id)


@router.put(
    "/progress",
    response_model=OnboardingProgressResponse,
    summary="Update Onboarding Progress",
    description="Update the user's current onboarding step for progress tracking." +
                (" **Development Mode**: Authentication bypassed." if IS_DEVELOPMENT else "")
)
async def update_onboarding_progress(
    progress_data: OnboardingProgressUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_authenticated_user)
):
    """Update onboarding progress to track which step the user is on."""
    return await OnboardingController.update_onboarding_progress(db, user.id, progress_data)
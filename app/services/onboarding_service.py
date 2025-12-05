from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, desc
from typing import Optional, List
import json
from datetime import datetime, date

from app.models import (
    UserProfile, UserGoal, TrainingPreferences, UserWorkoutPreference,
    OnboardingProgress, UserConsent, BodyWeightMeasurement, User
)
from app.enums import OnboardingStep
from app.schemas.onboarding_schemas import (
    UserProfileCreate, UserProfileUpdate, UserGoalCreate,
    TrainingPreferencesCreate, WorkoutPreferencesCreate,
    UserConsentCreate, BodyWeightCreate
)
from app.core.logger import get_logger

logger = get_logger("onboarding_service")


class OnboardingService:
    """Service for handling user onboarding flow."""

    @staticmethod
    async def get_or_create_profile(db: AsyncSession, user_id: str) -> UserProfile:
        """Get existing profile or create a new one - OPTIMIZED."""
        # Check if profile exists - single query without eager loading
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            # Create new profile with minimal data
            profile = UserProfile(
                user_id=user_id,
                unit_preference="imperial"
            )
            db.add(profile)
            # Flush to get ID without committing yet
            await db.flush()
            
            # Create onboarding progress in same transaction
            from app.models import OnboardingProgress
            onboarding = OnboardingProgress(
                profile_id=profile.id,
                current_step=OnboardingStep.BASIC_INFO,
                completed_steps="[]"
            )
            db.add(onboarding)
            await db.commit()
        
        return profile

    @staticmethod
    async def update_profile(
        db: AsyncSession, 
        profile_id: str, 
        profile_data: UserProfileUpdate
    ) -> Optional[UserProfile]:
        """Update user profile information - OPTIMIZED."""
        try:
            # Single query to get profile
            result = await db.execute(
                select(UserProfile).where(UserProfile.id == profile_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                return None
            
            # Update fields efficiently
            update_data = profile_data.dict(exclude_unset=True, exclude_none=True)
            for field, value in update_data.items():
                if hasattr(profile, field):
                    setattr(profile, field, value)
            
            # Single commit
            await db.commit()
            return profile
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating profile {profile_id}: {e}")
            raise

    @staticmethod
    async def create_goals(
        db: AsyncSession, 
        profile_id: str, 
        goals_data: List[UserGoalCreate]
    ) -> List[UserGoal]:
        """Create user fitness goals."""
        goals = []
        for goal_data in goals_data:
            # Convert enum values to strings
            goal_dict = goal_data.dict()
            if hasattr(goal_dict['goal_type'], 'value'):
                goal_dict['goal_type'] = goal_dict['goal_type'].value
            if hasattr(goal_dict['priority'], 'value'):
                goal_dict['priority'] = goal_dict['priority'].value
                
            goal = UserGoal(
                profile_id=profile_id,
                **goal_dict
            )
            db.add(goal)
            goals.append(goal)
        
        await db.commit()
        
        # Refresh all goals
        for goal in goals:
            await db.refresh(goal)
        
        # Mark goals step as completed
        await OnboardingService._update_onboarding_step(
            db, profile_id, OnboardingStep.GOALS, OnboardingStep.WEIGHT
        )
        
        return goals

    @staticmethod
    async def create_training_preferences(
        db: AsyncSession, 
        profile_id: str, 
        preferences_data: TrainingPreferencesCreate
    ) -> TrainingPreferences:
        """Create user training preferences."""
        preferences = TrainingPreferences(
            profile_id=profile_id,
            **preferences_data.dict()
        )
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)
        
        # Mark training preferences step as completed
        await OnboardingService._update_onboarding_step(
            db, profile_id, OnboardingStep.TRAINING_PREFERENCES, OnboardingStep.WORKOUT_PREFERENCES
        )
        
        return preferences

    @staticmethod
    async def create_workout_preferences(
        db: AsyncSession, 
        profile_id: str, 
        preferences_data: WorkoutPreferencesCreate
    ) -> List[UserWorkoutPreference]:
        """Create user workout preferences."""
        preferences = []
        for i, pref_data in enumerate(preferences_data.preferences):
            preference = UserWorkoutPreference(
                profile_id=profile_id,
                workout_type=pref_data.workout_type,
                rank=pref_data.rank or (i + 1)
            )
            db.add(preference)
            preferences.append(preference)
        
        await db.commit()
        
        # Refresh all preferences
        for pref in preferences:
            await db.refresh(pref)
        
        # Mark workout preferences step as completed
        await OnboardingService._update_onboarding_step(
            db, profile_id, OnboardingStep.WORKOUT_PREFERENCES, OnboardingStep.HEALTH_METRICS
        )
        
        return preferences

    @staticmethod
    async def add_weight_measurement(
        db: AsyncSession, 
        profile_id: str, 
        weight_data: BodyWeightCreate
    ) -> BodyWeightMeasurement:
        """Add body weight measurement."""
        # Get the user_id from profile
        result = await db.execute(
            select(UserProfile.user_id).where(UserProfile.id == profile_id)
        )
        user_id = result.scalar_one()
        
        measurement = BodyWeightMeasurement(
            user_id=user_id,
            value_lbs=float(weight_data.weight_lbs),
            notes=weight_data.notes,
            measured_at=datetime.utcnow()
        )
        db.add(measurement)
        await db.commit()
        await db.refresh(measurement)
        
        # Update onboarding progress - weight step completed, move to training preferences
        await OnboardingService._update_onboarding_step(
            db, profile_id, OnboardingStep.WEIGHT, OnboardingStep.TRAINING_PREFERENCES
        )
        
        return measurement

    @staticmethod
    async def complete_onboarding(db: AsyncSession, profile_id: str) -> OnboardingProgress:
        """Mark onboarding as completed."""
        result = await db.execute(
            select(OnboardingProgress).where(OnboardingProgress.profile_id == profile_id)
        )
        progress = result.scalar_one()
        
        progress.current_step = OnboardingStep.COMPLETED
        progress.is_completed = True
        progress.completed_at = datetime.utcnow()
        
        # Update completed steps
        completed_steps = json.loads(progress.completed_steps or "[]")
        if OnboardingStep.HEALTH_METRICS not in completed_steps:
            completed_steps.append(OnboardingStep.HEALTH_METRICS)
        progress.completed_steps = json.dumps(completed_steps)
        
        await db.commit()
        await db.refresh(progress)
        
        return progress

    @staticmethod
    async def get_onboarding_status(db: AsyncSession, user_id: str) -> dict:
        """Get complete onboarding status for a user."""
        # Get or create profile to ensure user always has onboarding data
        profile = await OnboardingService.get_or_create_profile(db, user_id)
        
        # Refresh profile with all related data
        await db.refresh(profile, [
            "goals", "training_preferences", "workout_preferences", "onboarding_progress"
        ])
        
        # Get latest weight measurement
        weight_result = await db.execute(
            select(BodyWeightMeasurement)
            .where(BodyWeightMeasurement.user_id == user_id)
            .order_by(desc(BodyWeightMeasurement.measured_at))
            .limit(1)
        )
        latest_weight = weight_result.scalar_one_or_none()
        
        return {
            "profile": profile,
            "onboarding_progress": profile.onboarding_progress,
            "goals": profile.goals,
            "training_preferences": profile.training_preferences,
            "workout_preferences": profile.workout_preferences,
            "latest_weight": latest_weight
        }

    @staticmethod
    async def _update_onboarding_step(
        db: AsyncSession, 
        profile_id: str, 
        completed_step: OnboardingStep, 
        next_step: OnboardingStep
    ):
        """Update onboarding progress."""
        result = await db.execute(
            select(OnboardingProgress).where(OnboardingProgress.profile_id == profile_id)
        )
        progress = result.scalar_one_or_none()
        
        if progress:
            # Update completed steps
            completed_steps = json.loads(progress.completed_steps or "[]")
            completed_step_value = completed_step.value  # Convert enum to string
            if completed_step_value not in completed_steps:
                completed_steps.append(completed_step_value)
            
            progress.completed_steps = json.dumps(completed_steps)
            progress.current_step = next_step  # This will be stored as enum in DB
            
            await db.commit()

    @staticmethod
    async def create_consent(
        db: AsyncSession, 
        profile_id: str, 
        consent_data: UserConsentCreate
    ) -> UserConsent:
        """Create user consent record."""
        # Get the user_id from profile
        result = await db.execute(
            select(UserProfile.user_id).where(UserProfile.id == profile_id)
        )
        user_id = result.scalar_one()
        
        consent = UserConsent(
            user_id=user_id,
            consent_type=consent_data.consent_type,
            granted=consent_data.granted,
            version=consent_data.version,
            granted_at=datetime.utcnow() if consent_data.granted else None
        )
        db.add(consent)
        await db.commit()
        await db.refresh(consent)
        
        return consent

    @staticmethod
    async def get_current_weight(db: AsyncSession, user_id: str) -> BodyWeightMeasurement:
        """Get the user's most recent weight measurement."""
        result = await db.execute(
            select(BodyWeightMeasurement)
            .where(BodyWeightMeasurement.user_id == user_id)
            .order_by(BodyWeightMeasurement.measured_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_target_weight(db: AsyncSession, user_id: str) -> dict:
        """Get the user's target weight from their weight-related goals."""
        # Get profile first
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            return None

        # Look for weight-related goals
        result = await db.execute(
            select(UserGoal)
            .where(
                UserGoal.profile_id == profile.id,
                UserGoal.goal_type.in_(["weight_loss", "weight_gain"]),
                UserGoal.active == True
            )
            .order_by(UserGoal.created_at.desc())
            .limit(1)
        )
        goal = result.scalar_one_or_none()

        if not goal:
            return None

        return {
            "target_value": goal.target_value,
            "goal_type": goal.goal_type,
            "target_date": goal.target_date,
            "description": goal.description
        }

    @staticmethod
    async def update_onboarding_progress(
        db: AsyncSession,
        user_id: str,
        current_step: str,
        current_frontend_step: Optional[str] = None
    ) -> OnboardingProgress:
        """Update onboarding progress to a specific step."""
        # Get or create profile
        profile = await OnboardingService.get_or_create_profile(db, user_id)

        # Get onboarding progress
        result = await db.execute(
            select(OnboardingProgress).where(OnboardingProgress.profile_id == profile.id)
        )
        progress = result.scalar_one_or_none()

        if not progress:
            # Create new progress if doesn't exist
            progress = OnboardingProgress(
                profile_id=profile.id,
                current_step=OnboardingStep(current_step),
                completed_steps=json.dumps([current_step])
            )
            if current_frontend_step:
                progress.current_frontend_step = current_frontend_step
            db.add(progress)
        else:
            # Update current step
            progress.current_step = OnboardingStep(current_step)
            # Explicitly update the timestamp to ensure it changes
            progress.updated_at = datetime.utcnow()

            # Save the frontend step for precise resume
            if current_frontend_step:
                progress.current_frontend_step = current_frontend_step

            # Track completed backend steps
            completed_steps = json.loads(progress.completed_steps or "[]")
            if current_step not in completed_steps:
                completed_steps.append(current_step)
                progress.completed_steps = json.dumps(completed_steps)

        await db.commit()
        await db.refresh(progress)

        return progress

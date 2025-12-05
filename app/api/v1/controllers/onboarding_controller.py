from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, date

from app.services.onboarding_service import OnboardingService
from app.models.user_profile import UserProfile
from app.models import OnboardingProgress  # Add missing import
from app.enums import OnboardingStep  # Add missing import
from app.schemas.onboarding_schemas import (
    UserProfileCreate, UserProfileUpdate, UserGoalCreate,
    TrainingPreferencesCreate, WorkoutPreferencesCreate,
    UserConsentCreate, BodyWeightCreate, WeightDataCreate, MainTargetCreate, FitnessDataCreate,
    UserMedicalConditionsCreate, MedicalConditionResponse, OnboardingProgressUpdate,
    UserProfileResponse, UserGoalResponse, TrainingPreferencesResponse,
    WorkoutPreferenceResponse, OnboardingProgressResponse,
    UserConsentResponse, BodyWeightResponse, OnboardingStatusResponse
)
from app.core.logger import get_logger

logger = get_logger("onboarding_controller")


class OnboardingController:
    """Controller for onboarding-related operations."""

    @staticmethod
    async def create_or_update_profile(
        db: AsyncSession, 
        user_id: str, 
        profile_data: UserProfileCreate | UserProfileUpdate
    ) -> UserProfileResponse:
        """Create or update user profile (upsert operation) - ULTRA OPTIMIZED."""
        try:
            # OPTIMIZATION: Use PostgreSQL UPSERT (ON CONFLICT) for maximum performance
            from sqlalchemy.dialects.postgresql import insert

            update_data = profile_data.dict(exclude_unset=True, exclude_none=True)

            # Convert enum to its value (not string representation)
            if 'gender' in update_data and update_data['gender']:
                # Handle both enum objects and string values
                gender_value = update_data['gender']
                if hasattr(gender_value, 'value'):
                    # It's an enum, get the value
                    update_data['gender'] = gender_value.value
                else:
                    # It's already a string, keep it as is
                    update_data['gender'] = gender_value

            import time
            start_time = time.time()
            logger.info(f"Update data being saved: {update_data}")

            # Calculate age if birth_date is provided
            if update_data.get('birth_date'):
                update_data['age'] = OnboardingController._calculate_age(update_data['birth_date'])

            # Set timestamps
            now = datetime.utcnow()
            update_data['updated_at'] = now

            after_prep = time.time()
            logger.info(f"⏱️ Data prep took: {(after_prep - start_time)*1000:.2f}ms")

            # PostgreSQL UPSERT - single atomic operation
            stmt = insert(UserProfile).values(
                user_id=user_id,
                unit_preference="imperial",
                created_at=now,
                **update_data
            )

            # On conflict, update all fields except user_id and created_at
            update_fields = {k: stmt.excluded[k] for k in update_data.keys()}

            stmt = stmt.on_conflict_do_update(
                index_elements=['user_id'],
                set_=update_fields
            ).returning(UserProfile)

            after_stmt = time.time()
            logger.info(f"⏱️ Statement build took: {(after_stmt - after_prep)*1000:.2f}ms")

            # Execute single UPSERT query
            result = await db.execute(stmt)

            after_execute = time.time()
            logger.info(f"⏱️ Query execution took: {(after_execute - after_stmt)*1000:.2f}ms")

            # Single commit
            await db.commit()

            after_commit = time.time()
            logger.info(f"⏱️ Commit took: {(after_commit - after_execute)*1000:.2f}ms")

            # Get the result row
            profile = result.scalar_one()

            after_fetch = time.time()
            logger.info(f"⏱️ Fetch result took: {(after_fetch - after_commit)*1000:.2f}ms")

            # Format birth_date as string in MM/DD/YYYY format if it's a date object
            birth_date_str = None
            if profile.birth_date:
                if hasattr(profile.birth_date, 'strftime'):
                    birth_date_str = profile.birth_date.strftime("%m/%d/%Y")
                else:
                    birth_date_str = str(profile.birth_date)

            response = UserProfileResponse(
                id=profile.id,
                user_id=profile.user_id,
                first_name=profile.first_name,
                last_name=profile.last_name,
                gender=profile.gender,
                birth_date=birth_date_str,
                height_inches=profile.height_inches,
                unit_preference=profile.unit_preference or "imperial",
                age=profile.age or 0,
                created_at=profile.created_at,
                updated_at=profile.updated_at
            )

            after_response = time.time()
            logger.info(f"⏱️ Response build took: {(after_response - after_fetch)*1000:.2f}ms")
            logger.info(f"⏱️ TOTAL TIME: {(after_response - start_time)*1000:.2f}ms")

            logger.info(f"UPSERT profile for user {user_id}")

            return response
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error UPSERT profile for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save profile"
            )

    @staticmethod
    async def get_user_profile(db: AsyncSession, user_id: str) -> UserProfileResponse:
        """Get user profile by user ID."""
        try:
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found"
                )

            # Helper function to safely format birth_date
            def safe_format_birth_date(birth_date):
                if birth_date is None:
                    return None
                if isinstance(birth_date, str):
                    return birth_date  # Already formatted
                if hasattr(birth_date, 'strftime'):
                    return birth_date.strftime("%m/%d/%Y")
                return None

            # Convert to response format with safe date formatting
            return UserProfileResponse(
                id=profile.id,
                user_id=profile.user_id,
                first_name=profile.first_name,
                last_name=profile.last_name,
                gender=profile.gender,
                birth_date=safe_format_birth_date(profile.birth_date),
                height_inches=profile.height_inches,
                unit_preference=profile.unit_preference,
                age=profile.age,
                created_at=profile.created_at,
                updated_at=profile.updated_at
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching profile for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch profile"
            )

    @staticmethod
    def _calculate_age(birth_date: date) -> int:
        """Calculate age from birth date."""
        today = date.today()
        age = today.year - birth_date.year
        
        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
            
        return max(0, age)

    @staticmethod
    async def update_profile(
        db: AsyncSession, 
        user_id: str, 
        profile_data: UserProfileUpdate
    ) -> UserProfileResponse:
        """Update user profile."""
        try:
            # First check if profile exists (without loading relationships)
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                # Create new profile without onboarding progress for now
                profile = UserProfile(
                    user_id=user_id,
                    unit_preference="imperial"
                )
                db.add(profile)
                await db.commit()
                await db.refresh(profile)
            
            # Update profile
            updated_profile = await OnboardingService.update_profile(
                db, profile.id, profile_data
            )
            
            if not updated_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Profile not found"
                )
            
            return UserProfileResponse(
                id=updated_profile.id,
                user_id=updated_profile.user_id,
                first_name=updated_profile.first_name,
                last_name=updated_profile.last_name,
                gender=updated_profile.gender,
                birth_date=updated_profile.birth_date.strftime("%m/%d/%Y") if updated_profile.birth_date else None,
                height_inches=updated_profile.height_inches,
                unit_preference=updated_profile.unit_preference,
                age=updated_profile.age,
                created_at=updated_profile.created_at,
                updated_at=updated_profile.updated_at
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update profile: {str(e)}"
            )

    @staticmethod
    async def create_goals(
        db: AsyncSession, 
        user_id: str, 
        goals_data: List[UserGoalCreate]
    ) -> List[UserGoalResponse]:
        """Create user goals."""
        try:
            # Get profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)
            
            # Create goals
            goals = await OnboardingService.create_goals(db, profile.id, goals_data)
            
            return [UserGoalResponse.from_orm(goal) for goal in goals]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create goals: {str(e)}"
            )

    @staticmethod
    async def create_training_preferences(
        db: AsyncSession, 
        user_id: str, 
        preferences_data: TrainingPreferencesCreate
    ) -> TrainingPreferencesResponse:
        """Create training preferences."""
        try:
            # Get profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)
            
            # Create preferences
            preferences = await OnboardingService.create_training_preferences(
                db, profile.id, preferences_data
            )
            
            return TrainingPreferencesResponse.from_orm(preferences)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create training preferences: {str(e)}"
            )

    @staticmethod
    async def create_workout_preferences(
        db: AsyncSession, 
        user_id: str, 
        preferences_data: WorkoutPreferencesCreate
    ) -> List[WorkoutPreferenceResponse]:
        """Create workout preferences."""
        try:
            # Get profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)
            
            # Create preferences
            preferences = await OnboardingService.create_workout_preferences(
                db, profile.id, preferences_data
            )
            
            return [WorkoutPreferenceResponse.from_orm(pref) for pref in preferences]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create workout preferences: {str(e)}"
            )

    @staticmethod
    async def add_weight_measurement(
        db: AsyncSession, 
        user_id: str, 
        weight_data: BodyWeightCreate
    ) -> BodyWeightResponse:
        """Add weight measurement."""
        try:
            # Get profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)
            
            # Add measurement
            measurement = await OnboardingService.add_weight_measurement(
                db, profile.id, weight_data
            )
            
            return BodyWeightResponse.from_orm(measurement)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add weight measurement: {str(e)}"
            )

    @staticmethod
    async def complete_onboarding(
        db: AsyncSession, 
        user_id: str
    ) -> OnboardingProgressResponse:
        """Complete onboarding process."""
        try:
            # Get profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)
            
            # Complete onboarding
            progress = await OnboardingService.complete_onboarding(db, profile.id)
            
            return OnboardingProgressResponse.from_orm(progress)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete onboarding: {str(e)}"
            )

    @staticmethod
    async def get_onboarding_status(
        db: AsyncSession, 
        user_id: str
    ) -> OnboardingStatusResponse:
        """Get complete onboarding status."""
        try:
            status_data = await OnboardingService.get_onboarding_status(db, user_id)
            
            # Get current weight and target weight
            current_weight_data = await OnboardingService.get_current_weight(db, user_id)
            target_weight_data = await OnboardingService.get_target_weight(db, user_id)
            
            current_weight_lbs = current_weight_data.value_lbs if current_weight_data else None
            target_weight_lbs = float(target_weight_data["target_value"]) if target_weight_data and target_weight_data["target_value"] else None
            weight_goal_type = target_weight_data["goal_type"] if target_weight_data else None
            
            return OnboardingStatusResponse(
                profile=UserProfileResponse(
                    id=status_data["profile"].id,
                    user_id=status_data["profile"].user_id,
                    first_name=status_data["profile"].first_name,
                    last_name=status_data["profile"].last_name,
                    gender=status_data["profile"].gender,
                    birth_date=status_data["profile"].birth_date.strftime("%m/%d/%Y") if status_data["profile"].birth_date else None,
                    height_inches=status_data["profile"].height_inches,
                    unit_preference=status_data["profile"].unit_preference,
                    age=status_data["profile"].age,
                    created_at=status_data["profile"].created_at,
                    updated_at=status_data["profile"].updated_at
                ),
                onboarding_progress=(
                    OnboardingProgressResponse.from_orm(status_data["onboarding_progress"])
                    if status_data["onboarding_progress"] else None
                ),
                goals=[UserGoalResponse.from_orm(goal) for goal in status_data["goals"]],
                training_preferences=(
                    TrainingPreferencesResponse.from_orm(status_data["training_preferences"])
                    if status_data["training_preferences"] else None
                ),
                workout_preferences=[
                    WorkoutPreferenceResponse.from_orm(pref) 
                    for pref in status_data["workout_preferences"]
                ],
                latest_weight=(
                    BodyWeightResponse.from_orm(status_data["latest_weight"])
                    if status_data["latest_weight"] else None
                ),
                current_weight_lbs=current_weight_lbs,
                target_weight_lbs=target_weight_lbs,
                weight_goal_type=weight_goal_type
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get onboarding status: {str(e)}"
            )

    @staticmethod
    async def create_consent(
        db: AsyncSession, 
        user_id: str, 
        consent_data: UserConsentCreate
    ) -> UserConsentResponse:
        """Create user consent."""
        try:
            # Get profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)
            
            # Create consent
            consent = await OnboardingService.create_consent(
                db, profile.id, consent_data
            )
            
            return UserConsentResponse.from_orm(consent)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create consent: {str(e)}"
            )

    @staticmethod
    async def get_current_weight(db: AsyncSession, user_id: str) -> dict:
        """Get the user's most recent weight measurement."""
        try:
            weight_measurement = await OnboardingService.get_current_weight(db, user_id)
            if not weight_measurement:
                return {
                    "current_weight_lbs": None,
                    "measured_at": None,
                    "message": "No weight measurements found"
                }
            
            return {
                "current_weight_lbs": weight_measurement.value_lbs,
                "measured_at": weight_measurement.measured_at,
                "notes": weight_measurement.notes
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get current weight: {str(e)}"
            )

    @staticmethod
    async def get_target_weight(db: AsyncSession, user_id: str) -> dict:
        """Get the user's target weight from their weight-related goals."""
        try:
            target_weight_info = await OnboardingService.get_target_weight(db, user_id)
            if not target_weight_info:
                return {
                    "target_weight_lbs": None,
                    "goal_type": None,
                    "message": "No weight-related goals found"
                }
            
            return {
                "target_weight_lbs": float(target_weight_info["target_value"]) if target_weight_info["target_value"] else None,
                "goal_type": target_weight_info["goal_type"],
                "target_date": target_weight_info["target_date"],
                "description": target_weight_info["description"]
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get target weight: {str(e)}"
            )

    @staticmethod
    async def set_target_weight(db: AsyncSession, user_id: str, target_data) -> dict:
        """Set the user's target weight goal."""
        try:
            # Create a weight goal using the target weight data
            from app.schemas.onboarding_schemas import UserGoalCreate
            from datetime import datetime

            # Get profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)

            # Parse target date if provided
            target_date = None
            if target_data.target_date:
                try:
                    target_date = datetime.strptime(target_data.target_date, "%m/%d/%Y")
                except ValueError:
                    # If parsing fails, set to None
                    target_date = None

            # Create goal data
            goal_data = UserGoalCreate(
                goal_type=target_data.goal_type,
                description=target_data.description or f"Target weight: {target_data.target_weight_lbs} lbs",
                target_value=target_data.target_weight_lbs,
                unit="lbs",
                target_date=target_date,
                priority="high"
            )

            # Create the goal
            goals = await OnboardingService.create_goals(db, profile.id, [goal_data])
            goal = goals[0]

            return {
                "target_weight_lbs": float(target_data.target_weight_lbs),
                "goal_type": target_data.goal_type,
                "target_date": target_data.target_date,
                "description": goal.description,
                "goal_id": goal.id,
                "message": "Target weight goal created successfully"
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to set target weight: {str(e)}"
            )

    @staticmethod
    async def save_main_target(
        db: AsyncSession,
        user_id: str,
        target_data: MainTargetCreate
    ) -> dict:
        """Save user's main fitness target (vo2_max or race_time)."""
        try:
            from app.models.user_goals import UserGoal
            import cuid
            from datetime import datetime

            # Get or create profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)

            # Create a goal with the main target
            goal_description = (
                "Improve VO₂ Max - Cardiovascular endurance"
                if target_data.main_target == "vo2_max"
                else "Improve Race Time - Speed and performance"
            )

            # Create goal directly (bypassing enum validation)
            goal = UserGoal(
                id=cuid.cuid(),
                profile_id=profile.id,
                goal_type=target_data.main_target,  # 'vo2_max' or 'race_time'
                description=goal_description,
                priority="high",
                active=True,
                achieved=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.add(goal)
            await db.commit()
            await db.refresh(goal)

            logger.info(f"Saved main target for user {user_id}: {target_data.main_target}")

            return {
                "success": True,
                "main_target": target_data.main_target,
                "goal_id": goal.id,
                "description": goal.description,
                "message": "Main target goal saved successfully"
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving main target for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save main target: {str(e)}"
            )

    @staticmethod
    async def save_fitness_data(
        db: AsyncSession,
        user_id: str,
        fitness_data: 'FitnessDataCreate'
    ) -> dict:
        """Save user's current fitness baseline (VO2 Max and Race Time)."""
        try:
            from app.models.vo2_max_estimate import VO2MaxEstimate
            from app.models.user_goals import UserGoal
            from datetime import datetime
            import cuid

            # Get or create profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)

            # 1. Save VO2 Max to vo2max_estimates table
            vo2_estimate = VO2MaxEstimate(
                id=cuid.cuid(),
                user_id=user_id,
                provider="manual_onboarding",
                measured_at=datetime.utcnow(),
                ml_per_kg_min=fitness_data.vo2_max,
                estimation_method="self_reported",
                context="onboarding",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(vo2_estimate)

            # 2. Save Race Time as a goal in user_goals table
            race_goal = UserGoal(
                id=cuid.cuid(),
                profile_id=profile.id,
                goal_type="race_time_baseline",
                description=f"Current race time: {fitness_data.race_time} minutes",
                target_value=str(fitness_data.race_time),
                unit="minutes",
                priority="medium",
                active=True,
                achieved=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(race_goal)

            await db.commit()
            await db.refresh(vo2_estimate)
            await db.refresh(race_goal)

            logger.info(f"Saved fitness data for user {user_id}: VO2={fitness_data.vo2_max}, Race Time={fitness_data.race_time}")

            return {
                "success": True,
                "vo2_max": fitness_data.vo2_max,
                "race_time": fitness_data.race_time,
                "vo2_estimate_id": vo2_estimate.id,
                "race_goal_id": race_goal.id,
                "message": "Fitness data saved successfully"
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving fitness data for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save fitness data: {str(e)}"
            )

    @staticmethod
    async def save_weight_data(
        db: AsyncSession,
        user_id: str,
        weight_data: WeightDataCreate
    ) -> dict:
        """Save both current and target weight in a single call."""
        try:
            from datetime import datetime

            # Get or create profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)

            # 1. Save current weight as a measurement
            current_weight_create = BodyWeightCreate(
                weight_lbs=weight_data.current_weight_lbs,
                notes=weight_data.notes
            )
            current_measurement = await OnboardingService.add_weight_measurement(
                db, profile.id, current_weight_create
            )

            # 2. Save target weight as a goal
            target_date = None
            if weight_data.target_date:
                try:
                    target_date = datetime.strptime(weight_data.target_date, "%m/%d/%Y")
                except ValueError:
                    target_date = None

            goal_description = f"{weight_data.goal_type.replace('_', ' ').title()}: Target {weight_data.target_weight_lbs} lbs"

            goal_data = UserGoalCreate(
                goal_type=weight_data.goal_type,
                description=goal_description,
                target_value=weight_data.target_weight_lbs,
                unit="lbs",
                target_date=target_date,
                priority="high"
            )

            goals = await OnboardingService.create_goals(db, profile.id, [goal_data])
            target_goal = goals[0]

            logger.info(f"Saved weight data for user {user_id}: current={weight_data.current_weight_lbs}lbs, target={weight_data.target_weight_lbs}lbs")

            return {
                "success": True,
                "current_weight": {
                    "id": current_measurement.id,
                    "value_lbs": current_measurement.value_lbs,
                    "measured_at": current_measurement.measured_at
                },
                "target_weight": {
                    "id": target_goal.id,
                    "value_lbs": float(weight_data.target_weight_lbs),
                    "goal_type": weight_data.goal_type,
                    "target_date": weight_data.target_date
                },
                "message": "Weight data saved successfully"
            }
        except Exception as e:
            logger.error(f"Error saving weight data for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save weight data: {str(e)}"
            )

    @staticmethod
    async def update_onboarding_progress(
        db: AsyncSession,
        user_id: str,
        progress_data: OnboardingProgressUpdate
    ) -> OnboardingProgressResponse:
        """Update onboarding progress."""
        try:
            progress = await OnboardingService.update_onboarding_progress(
                db, user_id, progress_data.current_step, progress_data.current_frontend_step
            )

            return OnboardingProgressResponse.from_orm(progress)
        except Exception as e:
            logger.error(f"Error updating onboarding progress for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update onboarding progress: {str(e)}"
            )

    @staticmethod
    async def get_medical_conditions(db: AsyncSession) -> List[dict]:
        """Get all active medical conditions for display."""
        try:
            from app.models.medical_condition import MedicalCondition
            from sqlalchemy import select

            # Fetch all active medical conditions, ordered by display_order
            result = await db.execute(
                select(MedicalCondition)
                .where(MedicalCondition.is_active == True)
                .order_by(MedicalCondition.display_order)
            )
            conditions = result.scalars().all()

            return [
                {
                    "id": condition.id,
                    "name": condition.name,
                    "description": condition.description,
                    "category": condition.category,
                    "display_order": condition.display_order
                }
                for condition in conditions
            ]
        except Exception as e:
            logger.error(f"Error fetching medical conditions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch medical conditions: {str(e)}"
            )

    @staticmethod
    async def save_user_medical_conditions(
        db: AsyncSession,
        user_id: str,
        conditions_data: 'UserMedicalConditionsCreate'
    ) -> dict:
        """Save user's selected medical conditions."""
        try:
            from app.models.user_medical_condition import UserMedicalCondition
            import cuid
            from datetime import datetime

            # Get or create profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)

            # Delete existing medical conditions for this user
            await db.execute(
                select(UserMedicalCondition).where(UserMedicalCondition.profile_id == profile.id)
            )
            existing = (await db.execute(
                select(UserMedicalCondition).where(UserMedicalCondition.profile_id == profile.id)
            )).scalars().all()
            
            for existing_condition in existing:
                await db.delete(existing_condition)

            # Add new medical conditions
            saved_conditions = []
            for condition_id in conditions_data.condition_ids:
                user_condition = UserMedicalCondition(
                    id=cuid.cuid(),
                    profile_id=profile.id,
                    medical_condition_id=condition_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(user_condition)
                saved_conditions.append(condition_id)

            await db.commit()

            logger.info(f"Saved medical conditions for user {user_id}: {saved_conditions}")

            return {
                "success": True,
                "condition_ids": saved_conditions,
                "message": f"Saved {len(saved_conditions)} medical condition(s)"
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving medical conditions for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save medical conditions: {str(e)}"
            )

    @staticmethod
    async def save_fitness_status(
        db: AsyncSession,
        user_id: str,
        status_data: 'FitnessStatusCreate'
    ) -> dict:
        """Save user's fitness status level (beginner/intermediate/advanced)."""
        try:
            from app.models.training_preferences import TrainingPreferences
            from app.enums import TrainingLevel
            import cuid
            from datetime import datetime
            from sqlalchemy import select

            # Get or create profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)

            # Check if training preferences already exist
            result = await db.execute(
                select(TrainingPreferences).where(TrainingPreferences.profile_id == profile.id)
            )
            training_prefs = result.scalars().first()

            if training_prefs:
                # Update existing
                training_prefs.training_level = TrainingLevel(status_data.fitness_status)
                training_prefs.updated_at = datetime.utcnow()
            else:
                # Create new training preferences with defaults
                training_prefs = TrainingPreferences(
                    id=cuid.cuid(),
                    profile_id=profile.id,
                    training_level=TrainingLevel(status_data.fitness_status),
                    sessions_per_day=1,
                    days_per_week=3,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(training_prefs)

            await db.commit()
            await db.refresh(training_prefs)

            logger.info(f"Saved fitness status for user {user_id}: {status_data.fitness_status}")

            return {
                "success": True,
                "fitness_status": status_data.fitness_status,
                "message": "Fitness status saved successfully"
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving fitness status for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save fitness status: {str(e)}"
            )

    @staticmethod
    async def save_user_mood(
        db: AsyncSession,
        user_id: str,
        mood_data: 'UserMoodCreate'
    ) -> dict:
        """Save user's current mood."""
        try:
            from app.models.user_mood import UserMood
            from app.enums import MoodType
            import cuid
            from datetime import datetime

            # Get or create profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)

            # Create new mood entry
            user_mood = UserMood(
                id=cuid.cuid(),
                profile_id=profile.id,
                mood_type=MoodType(mood_data.mood.lower()),
                recorded_at=datetime.utcnow(),
                notes=mood_data.notes,
                created_at=datetime.utcnow()
            )
            db.add(user_mood)

            await db.commit()
            await db.refresh(user_mood)

            logger.info(f"Saved mood for user {user_id}: {mood_data.mood}")

            return {
                "success": True,
                "mood": mood_data.mood,
                "recorded_at": user_mood.recorded_at.isoformat(),
                "message": "Mood saved successfully"
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving mood for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save mood: {str(e)}"
            )

    @staticmethod
    async def save_daily_training_intention(
        db: AsyncSession,
        user_id: str,
        intention_data: 'DailyTrainingIntentionCreate'
    ) -> dict:
        """Save user's daily training intention (Yes/No/Maybe for training today)."""
        try:
            from app.models.user_daily_training_intention import UserDailyTrainingIntention
            from app.enums import DailyTrainingIntention
            import cuid
            from datetime import datetime, date

            # Get or create profile
            profile = await OnboardingService.get_or_create_profile(db, user_id)

            # Create new training intention entry
            training_intention = UserDailyTrainingIntention(
                id=cuid.cuid(),
                profile_id=profile.id,
                intention=DailyTrainingIntention(intention_data.intention.lower()),
                intention_date=date.today(),
                notes=intention_data.notes,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(training_intention)

            await db.commit()
            await db.refresh(training_intention)

            logger.info(f"Saved daily training intention for user {user_id}: {intention_data.intention}")

            return {
                "success": True,
                "intention": intention_data.intention,
                "intention_date": training_intention.intention_date.isoformat(),
                "message": "Daily training intention saved successfully"
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving daily training intention for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save daily training intention: {str(e)}"
            )

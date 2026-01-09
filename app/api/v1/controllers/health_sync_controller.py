"""
Health Sync Controller
Handles HTTP request/response logic for health data sync endpoints
"""

from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List
from pydantic import BaseModel, Field
from typing import Optional

from app.services.health_sync_service import HealthSyncService
from app.core.logger import get_logger

logger = get_logger("health_sync_controller")


# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================

class HeartRateSampleInput(BaseModel):
    """Single heart rate sample"""
    bpm: int = Field(..., ge=30, le=250, description="Heart rate in beats per minute")
    captured_at: str = Field(..., description="ISO 8601 timestamp when sample was captured")
    context: Optional[str] = Field(default="unknown", description="Context: resting, workout, sleep, unknown")
    source_record_id: Optional[str] = Field(default=None, description="Provider's unique ID for this record")

    class Config:
        json_schema_extra = {
            "example": {
                "bpm": 84,
                "captured_at": "2025-10-22T19:41:00.000Z",
                "context": "unknown",
                "source_record_id": "hr_2025-10-22T19:41:00_84"
            }
        }


class HeartRateBatchInput(BaseModel):
    """Batch of heart rate samples"""
    provider: str = Field(..., description="Data provider: apple_healthkit, fitbit, etc.")
    samples: List[HeartRateSampleInput]

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "apple_healthkit",
                "samples": [
                    {
                        "bpm": 84,
                        "captured_at": "2025-10-22T19:41:00.000Z",
                        "context": "unknown",
                        "source_record_id": "hr_2025-10-22T19:41:00_84"
                    }
                ]
            }
        }


class StepSampleInput(BaseModel):
    """Single step sample"""
    steps: int = Field(..., ge=0, description="Number of steps")
    start_minute: str = Field(..., description="ISO 8601 timestamp for start of period")
    source_record_id: Optional[str] = Field(default=None, description="Provider's unique ID")

    class Config:
        json_schema_extra = {
            "example": {
                "steps": 12453,
                "start_minute": "2025-10-22T00:00:00.000Z",
                "source_record_id": "steps_2025-10-22"
            }
        }


class StepsBatchInput(BaseModel):
    """Batch of step samples"""
    provider: str
    samples: List[StepSampleInput]


class VO2MaxSampleInput(BaseModel):
    """Single VO2 max sample"""
    ml_per_kg_min: float = Field(..., ge=10.0, le=90.0, description="VO2 max in ml/kg/min")
    measured_at: str = Field(..., description="ISO 8601 timestamp")
    estimation_method: str = Field(default="apple_health", description="Method: apple_health, fitbit_cardio_fitness, lab, field_test")
    source_record_id: Optional[str] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "ml_per_kg_min": 42.5,
                "measured_at": "2025-10-16T14:30:00.000Z",
                "estimation_method": "apple_health",
                "source_record_id": "vo2_2025-10-16_42.5"
            }
        }


class VO2MaxBatchInput(BaseModel):
    """Batch of VO2 max samples"""
    provider: str
    samples: List[VO2MaxSampleInput]


class WorkoutInput(BaseModel):
    """Single workout session"""
    activity_type: str = Field(..., description="Type of workout: Running, Cycling, etc.")
    start_time: str = Field(..., description="ISO 8601 start time")
    end_time: str = Field(..., description="ISO 8601 end time")
    duration_seconds: int = Field(..., ge=0, description="Duration in seconds")
    calories: Optional[float] = Field(default=None, ge=0, description="Calories burned")
    distance_miles: Optional[float] = Field(default=None, ge=0, description="Distance in miles")
    source_record_id: Optional[str] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "activity_type": "Running",
                "start_time": "2025-10-22T06:00:00.000Z",
                "end_time": "2025-10-22T06:45:00.000Z",
                "duration_seconds": 2700,
                "calories": 285.5,
                "distance_miles": 3.2,
                "source_record_id": "workout_2025-10-22_Running"
            }
        }


class WorkoutsBatchInput(BaseModel):
    """Batch of workouts"""
    provider: str
    workouts: List[WorkoutInput]


class SyncResponse(BaseModel):
    """Standard sync response"""
    success: bool
    data: dict

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total_received": 100,
                    "total_stored": 98,
                    "duplicates_skipped": 2
                }
            }
        }


# ============================================================================
# Controller Class
# ============================================================================

class HealthSyncController:
    """Controller for health data sync operations."""

    @staticmethod
    async def sync_heart_rate_batch(
        request: Request,
        db: AsyncSession,
        payload: HeartRateBatchInput
    ) -> Dict:
        """Sync batch of heart rate samples from mobile device."""
        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user
            user_id = user.id

            service = HealthSyncService(db)
            result = await service.sync_heart_rate_batch(
                user_id=user_id,
                provider=payload.provider,
                samples=[s.model_dump() for s in payload.samples]
            )

            logger.info(f"Synced {result.get('total_stored', 0)} heart rate samples for user {user.email}")
            return SyncResponse(success=True, data=result).model_dump()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing heart rate data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync heart rate data: {str(e)}"
            )

    @staticmethod
    async def sync_steps_batch(
        request: Request,
        db: AsyncSession,
        payload: StepsBatchInput
    ) -> Dict:
        """Sync batch of step count samples."""
        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user
            user_id = user.id

            service = HealthSyncService(db)
            result = await service.sync_steps_batch(
                user_id=user_id,
                provider=payload.provider,
                samples=[s.model_dump() for s in payload.samples]
            )

            logger.info(f"Synced {result.get('total_stored', 0)} step samples for user {user.email}")
            return SyncResponse(success=True, data=result).model_dump()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing steps data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync steps data: {str(e)}"
            )

    @staticmethod
    async def sync_vo2max_batch(
        request: Request,
        db: AsyncSession,
        payload: VO2MaxBatchInput
    ) -> Dict:
        """Sync batch of VO2 max measurements."""
        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user
            user_id = user.id

            service = HealthSyncService(db)
            result = await service.sync_vo2max_batch(
                user_id=user_id,
                provider=payload.provider,
                samples=[s.model_dump() for s in payload.samples]
            )

            logger.info(f"Synced {result.get('total_stored', 0)} VO2 max samples for user {user.email}")
            return SyncResponse(success=True, data=result).model_dump()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing VO2 max data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync VO2 max data: {str(e)}"
            )

    @staticmethod
    async def sync_workouts_batch(
        request: Request,
        db: AsyncSession,
        payload: WorkoutsBatchInput
    ) -> Dict:
        """Sync batch of workout sessions."""
        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user
            user_id = user.id

            service = HealthSyncService(db)
            result = await service.sync_workouts_batch(
                user_id=user_id,
                provider=payload.provider,
                workouts=[w.model_dump() for w in payload.workouts]
            )

            logger.info(f"Synced {result.get('total_stored', 0)} workouts for user {user.email}")
            return SyncResponse(success=True, data=result).model_dump()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing workouts data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync workouts data: {str(e)}"
            )

    @staticmethod
    async def get_sync_status(
        request: Request,
        db: AsyncSession
    ) -> Dict:
        """Get sync status for current user."""
        try:
            # Check authentication
            if not hasattr(request.state, 'user'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )

            user = request.state.user
            user_id = user.id

            # TODO: Implement sync status query
            # Query latest HealthIngestBatch records for this user
            # Return summary of latest syncs

            return {
                "success": True,
                "data": {
                    "user_id": user_id,
                    "message": "Sync status endpoint - TODO: implement full status query"
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get sync status: {str(e)}"
            )

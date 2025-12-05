"""
Health Data Sync API Endpoints
Receives health data from mobile devices and stores in database
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.database.connection import get_db
from app.services.health_sync_service import HealthSyncService

router = APIRouter()


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
# API Endpoints
# ============================================================================

@router.post("/heart-rate/batch", response_model=SyncResponse)
async def sync_heart_rate_batch(
    payload: HeartRateBatchInput,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync batch of heart rate samples from mobile device

    - **provider**: Data source (e.g., apple_healthkit)
    - **samples**: Array of heart rate readings with timestamps

    Returns count of records received, stored, and skipped (duplicates)
    """
    try:
        # Get authenticated user from request state (set by ClerkAuthMiddleware)
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

        return SyncResponse(success=True, data=result)

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync heart rate data: {str(e)}"
        )


@router.post("/steps/batch", response_model=SyncResponse)
async def sync_steps_batch(
    payload: StepsBatchInput,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync batch of step count samples

    - **provider**: Data source (e.g., apple_healthkit)
    - **samples**: Array of step counts with timestamps
    """
    try:
        # Get authenticated user from request state (set by ClerkAuthMiddleware)
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

        return SyncResponse(success=True, data=result)

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync steps data: {str(e)}"
        )


@router.post("/vo2max/batch", response_model=SyncResponse)
async def sync_vo2max_batch(
    payload: VO2MaxBatchInput,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync batch of VO2 max measurements

    - **provider**: Data source (e.g., apple_healthkit)
    - **samples**: Array of VO2 max readings
    """
    try:
        # Get authenticated user from request state (set by ClerkAuthMiddleware)
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

        return SyncResponse(success=True, data=result)

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync VO2 max data: {str(e)}"
        )


@router.post("/workouts/batch", response_model=SyncResponse)
async def sync_workouts_batch(
    payload: WorkoutsBatchInput,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync batch of workout sessions

    - **provider**: Data source (e.g., apple_healthkit)
    - **workouts**: Array of workout sessions with details
    """
    try:
        # Get authenticated user from request state (set by ClerkAuthMiddleware)
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

        return SyncResponse(success=True, data=result)

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync workouts data: {str(e)}"
        )


@router.get("/sync-status")
async def get_sync_status(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Get sync status for current user
    Returns latest sync batches and record counts
    """
    try:
        # Get authenticated user from request state (set by ClerkAuthMiddleware)
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
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )

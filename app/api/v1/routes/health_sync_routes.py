"""
Health Data Sync Routes
Receives health data from mobile devices and stores in database
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.middlewares.clerk_auth import get_authenticated_user
from app.models.user import User
from app.api.v1.controllers.health_sync_controller import (
    HealthSyncController,
    HeartRateBatchInput,
    StepsBatchInput,
    VO2MaxBatchInput,
    WorkoutsBatchInput,
    SyncResponse
)

router = APIRouter()


@router.post("/heart-rate/batch", response_model=SyncResponse)
async def sync_heart_rate_batch(
    payload: HeartRateBatchInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authenticated_user)
):
    """
    Sync batch of heart rate samples from mobile device

    - **provider**: Data source (e.g., apple_healthkit)
    - **samples**: Array of heart rate readings with timestamps

    Returns count of records received, stored, and skipped (duplicates)
    """
    return await HealthSyncController.sync_heart_rate_batch(request, db, payload)


@router.post("/steps/batch", response_model=SyncResponse)
async def sync_steps_batch(
    payload: StepsBatchInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authenticated_user)
):
    """
    Sync batch of step count samples

    - **provider**: Data source (e.g., apple_healthkit)
    - **samples**: Array of step counts with timestamps
    """
    return await HealthSyncController.sync_steps_batch(request, db, payload)


@router.post("/vo2max/batch", response_model=SyncResponse)
async def sync_vo2max_batch(
    payload: VO2MaxBatchInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authenticated_user)
):
    """
    Sync batch of VO2 max measurements

    - **provider**: Data source (e.g., apple_healthkit)
    - **samples**: Array of VO2 max readings
    """
    return await HealthSyncController.sync_vo2max_batch(request, db, payload)


@router.post("/workouts/batch", response_model=SyncResponse)
async def sync_workouts_batch(
    payload: WorkoutsBatchInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authenticated_user)
):
    """
    Sync batch of workout sessions

    - **provider**: Data source (e.g., apple_healthkit)
    - **workouts**: Array of workout sessions with details
    """
    return await HealthSyncController.sync_workouts_batch(request, db, payload)


@router.get("/sync-status")
async def get_sync_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authenticated_user)
):
    """
    Get sync status for current user
    Returns latest sync batches and record counts
    """
    return await HealthSyncController.get_sync_status(request, db)

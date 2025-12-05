"""
Health Data Sync Service
Handles ingestion of health data from various providers (Apple HealthKit, etc.)
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from app.models.heart_rate_sample import HeartRateSample
from app.models.step_minute import StepMinute
from app.models.vo2_max_estimate import VO2MaxEstimate
from app.models.workout_session import WorkoutSession
from app.models.device import Device
from app.models.health_ingest_batch import HealthIngestBatch

logger = logging.getLogger(__name__)


class HealthSyncService:
    """Service for syncing health data from devices to database"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_device(
        self,
        user_id: str,
        provider: str,
        device_name: Optional[str] = None
    ) -> Device:
        """Get existing device or create new one"""
        stmt = select(Device).where(
            Device.user_id == user_id,
            Device.provider == provider
        )
        result = await self.db.execute(stmt)
        device = result.scalars().first()  # Use first() to handle multiple duplicates

        if not device:
            device = Device(
                user_id=user_id,
                provider=provider,
                name=device_name or f"{provider.replace('_', ' ').title()}"
            )
            self.db.add(device)
            await self.db.flush()
            logger.info(f"Created new device: {device.id} for user {user_id}, provider {provider}")

        return device

    def create_ingest_batch(
        self,
        user_id: str,
        provider: str,
        device_id: str,
        count_received: int
    ) -> HealthIngestBatch:
        """Create a new health ingest batch record"""
        batch = HealthIngestBatch(
            user_id=user_id,
            provider=provider,
            device_id=device_id,
            count_received=count_received,
            count_stored=0
        )
        self.db.add(batch)
        return batch

    async def sync_heart_rate_batch(
        self,
        user_id: str,
        provider: str,
        samples: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Sync batch of heart rate samples
        Returns: {'total_received', 'total_stored', 'duplicates_skipped'}
        """
        logger.info(f"Syncing {len(samples)} heart rate samples for user {user_id}")

        # Get or create device
        device = await self.get_or_create_device(user_id, provider, "Apple Health")

        # Create ingest batch
        batch = self.create_ingest_batch(user_id, provider, device.id, len(samples))
        await self.db.flush()

        stored = 0
        skipped = 0

        # Prefetch existing source IDs to minimize per-row queries
        source_ids = {sample.get('source_record_id') for sample in samples if sample.get('source_record_id')}
        existing_source_ids = set()
        if source_ids:
            existing_stmt = select(HeartRateSample.source_record_id).where(
                HeartRateSample.user_id == user_id,
                HeartRateSample.provider == provider,
                HeartRateSample.source_record_id.in_(source_ids)
            )
            result = await self.db.execute(existing_stmt)
            existing_source_ids = set(result.scalars().all())

        for sample in samples:
            try:
                # Check for duplicate using source_record_id
                source_id = sample.get('source_record_id')
                if source_id:
                    if source_id in existing_source_ids:
                        skipped += 1
                        continue
                    # track within-batch duplicates
                    existing_source_ids.add(source_id)

                # Parse datetime and strip timezone (PostgreSQL expects naive datetime)
                captured_at = datetime.fromisoformat(sample['captured_at'].replace('Z', '+00:00')).replace(tzinfo=None)

                # Create new sample
                hr_sample = HeartRateSample(
                    user_id=user_id,
                    device_id=device.id,
                    provider=provider,
                    source_record_id=source_id,
                    ingest_batch_id=batch.id,
                    captured_at=captured_at,
                    bpm=int(sample['bpm']),
                    context=sample.get('context', 'unknown')
                )
                self.db.add(hr_sample)
                stored += 1

            except Exception as e:
                logger.error(f"Error processing heart rate sample: {e}", exc_info=True)
                continue

        # Update batch with stored count
        batch.count_stored = stored
        await self.db.commit()

        logger.info(f"Heart rate sync complete: {stored} stored, {skipped} skipped")
        return {
            'total_received': len(samples),
            'total_stored': stored,
            'duplicates_skipped': skipped
        }

    async def sync_steps_batch(
        self,
        user_id: str,
        provider: str,
        samples: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Sync batch of step samples
        Returns: {'total_received', 'total_stored', 'duplicates_skipped'}
        """
        logger.info(f"Syncing {len(samples)} step samples for user {user_id}")

        device = await self.get_or_create_device(user_id, provider, "Apple Health")
        batch = self.create_ingest_batch(user_id, provider, device.id, len(samples))
        await self.db.flush()

        stored = 0
        skipped = 0

        source_ids = {sample.get('source_record_id') for sample in samples if sample.get('source_record_id')}
        existing_source_ids = set()
        if source_ids:
            existing_stmt = select(StepMinute.source_record_id).where(
                StepMinute.user_id == user_id,
                StepMinute.provider == provider,
                StepMinute.source_record_id.in_(source_ids)
            )
            result = await self.db.execute(existing_stmt)
            existing_source_ids = set(result.scalars().all())

        for sample in samples:
            try:
                source_id = sample.get('source_record_id')
                if source_id:
                    if source_id in existing_source_ids:
                        skipped += 1
                        continue
                    existing_source_ids.add(source_id)

                # Parse datetime and strip timezone (PostgreSQL expects naive datetime)
                start_minute = datetime.fromisoformat(sample['start_minute'].replace('Z', '+00:00')).replace(tzinfo=None)

                step_sample = StepMinute(
                    user_id=user_id,
                    device_id=device.id,
                    provider=provider,
                    source_record_id=source_id,
                    ingest_batch_id=batch.id,
                    start_minute=start_minute,
                    steps=int(sample['steps'])
                )
                self.db.add(step_sample)
                stored += 1

            except Exception as e:
                logger.error(f"Error processing step sample: {e}", exc_info=True)
                continue

        batch.count_stored = stored
        await self.db.commit()

        logger.info(f"Steps sync complete: {stored} stored, {skipped} skipped")
        return {
            'total_received': len(samples),
            'total_stored': stored,
            'duplicates_skipped': skipped
        }

    async def sync_vo2max_batch(
        self,
        user_id: str,
        provider: str,
        samples: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Sync batch of VO2 max samples
        Returns: {'total_received', 'total_stored', 'duplicates_skipped'}
        """
        logger.info(f"Syncing {len(samples)} VO2 max samples for user {user_id}")

        device = await self.get_or_create_device(user_id, provider, "Apple Health")
        batch = self.create_ingest_batch(user_id, provider, device.id, len(samples))
        await self.db.flush()

        stored = 0
        skipped = 0

        source_ids = {sample.get('source_record_id') for sample in samples if sample.get('source_record_id')}
        existing_source_ids = set()
        if source_ids:
            existing_stmt = select(VO2MaxEstimate.source_record_id).where(
                VO2MaxEstimate.user_id == user_id,
                VO2MaxEstimate.provider == provider,
                VO2MaxEstimate.source_record_id.in_(source_ids)
            )
            result = await self.db.execute(existing_stmt)
            existing_source_ids = set(result.scalars().all())

        for sample in samples:
            try:
                source_id = sample.get('source_record_id')
                if source_id:
                    if source_id in existing_source_ids:
                        skipped += 1
                        continue
                    existing_source_ids.add(source_id)

                # Parse datetime and strip timezone (PostgreSQL expects naive datetime)
                measured_at = datetime.fromisoformat(sample['measured_at'].replace('Z', '+00:00')).replace(tzinfo=None)

                vo2_sample = VO2MaxEstimate(
                    user_id=user_id,
                    device_id=device.id,
                    provider=provider,
                    source_record_id=source_id,
                    ingest_batch_id=batch.id,
                    measured_at=measured_at,
                    ml_per_kg_min=float(sample['ml_per_kg_min']),
                    estimation_method=sample.get('estimation_method', 'apple_health')
                )
                self.db.add(vo2_sample)
                stored += 1

            except Exception as e:
                logger.error(f"Error processing VO2 max sample: {e}", exc_info=True)
                continue

        batch.count_stored = stored
        await self.db.commit()

        logger.info(f"VO2 max sync complete: {stored} stored, {skipped} skipped")
        return {
            'total_received': len(samples),
            'total_stored': stored,
            'duplicates_skipped': skipped
        }

    async def sync_workouts_batch(
        self,
        user_id: str,
        provider: str,
        workouts: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Sync batch of workout sessions
        Returns: {'total_received', 'total_stored', 'duplicates_skipped'}
        """
        logger.info(f"Syncing {len(workouts)} workouts for user {user_id}")

        device = await self.get_or_create_device(user_id, provider, "Apple Health")
        batch = self.create_ingest_batch(user_id, provider, device.id, len(workouts))
        await self.db.flush()

        stored = 0
        skipped = 0

        for workout in workouts:
            try:
                source_id = workout.get('source_record_id')
                if source_id:
                    stmt = select(WorkoutSession).where(
                        WorkoutSession.user_id == user_id,
                        WorkoutSession.provider == provider,
                        WorkoutSession.source_record_id == source_id
                    )
                    result = await self.db.execute(stmt)
                    existing = result.scalars().first()  # Use first() to handle multiple duplicates

                    if existing:
                        skipped += 1
                        continue

                # Parse datetimes and strip timezone (PostgreSQL expects naive datetime)
                start_time = datetime.fromisoformat(workout['start_time'].replace('Z', '+00:00')).replace(tzinfo=None)
                end_time = datetime.fromisoformat(workout['end_time'].replace('Z', '+00:00')).replace(tzinfo=None)

                workout_session = WorkoutSession(
                    user_id=user_id,
                    device_id=device.id,
                    provider=provider,
                    source_record_id=source_id,
                    ingest_batch_id=batch.id,
                    activity_type=workout['activity_type'],
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=int(workout['duration_seconds']),
                    calories=float(workout['calories']) if workout.get('calories') else None,
                    distance_miles=float(workout['distance_miles']) if workout.get('distance_miles') else None
                )
                self.db.add(workout_session)
                stored += 1

            except Exception as e:
                logger.error(f"Error processing workout: {e}", exc_info=True)
                continue

        batch.count_stored = stored
        await self.db.commit()

        logger.info(f"Workouts sync complete: {stored} stored, {skipped} skipped")
        return {
            'total_received': len(workouts),
            'total_stored': stored,
            'duplicates_skipped': skipped
        }

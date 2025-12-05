"""add unique indexes to health metrics tables

Revision ID: 20241101_add_unique_indexes
Revises: 4d4650de0848
Create Date: 2025-11-01
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20241101_add_unique_indexes"
down_revision = "4d4650de0848"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # body_weight_measurements: unique per (user_id, measured_at)
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_body_weight_measurements_user_measured_at
            ON body_weight_measurements (user_id, measured_at)
            """
        )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_weight_user_timestamp'
            ) THEN
                ALTER TABLE body_weight_measurements
                ADD CONSTRAINT uq_weight_user_timestamp
                UNIQUE USING INDEX uq_body_weight_measurements_user_measured_at;
            END IF;
        END
        $$;
        """
    )

    # user_daily_training_intentions: unique per (profile_id, intention_date)
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_user_daily_training_intentions_profile_date
            ON user_daily_training_intentions (profile_id, intention_date)
            """
        )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_training_intention_profile_date'
            ) THEN
                ALTER TABLE user_daily_training_intentions
                ADD CONSTRAINT uq_training_intention_profile_date
                UNIQUE USING INDEX uq_user_daily_training_intentions_profile_date;
            END IF;
        END
        $$;
        """
    )

    # user_medical_conditions: unique per (profile_id, medical_condition_id)
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_user_medical_conditions_profile_condition
            ON user_medical_conditions (profile_id, medical_condition_id)
            """
        )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_medical_condition_profile'
            ) THEN
                ALTER TABLE user_medical_conditions
                ADD CONSTRAINT uq_medical_condition_profile
                UNIQUE USING INDEX uq_user_medical_conditions_profile_condition;
            END IF;
        END
        $$;
        """
    )

    # user_goals supporting indexes
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_goals_profile_active
            ON user_goals (profile_id, active)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_goals_profile_achieved
            ON user_goals (profile_id, achieved)
            """
        )

    # webhook_events processed flag index
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_webhook_processed_time
            ON webhook_events (processed, received_at)
            """
        )


def downgrade() -> None:
    # Drop webhook index
    with op.get_context().autocommit_block():
        op.execute(
            """
            DROP INDEX CONCURRENTLY IF EXISTS ix_webhook_processed_time
            """
        )

    # Drop user_goals indexes
    with op.get_context().autocommit_block():
        op.execute(
            """
            DROP INDEX CONCURRENTLY IF EXISTS ix_user_goals_profile_achieved
            """
        )
        op.execute(
            """
            DROP INDEX CONCURRENTLY IF EXISTS ix_user_goals_profile_active
            """
        )

    # Drop unique constraints/indexes for user_medical_conditions
    op.execute(
        """
        ALTER TABLE user_medical_conditions
        DROP CONSTRAINT IF EXISTS uq_medical_condition_profile
        """
    )
    with op.get_context().autocommit_block():
        op.execute(
            """
            DROP INDEX CONCURRENTLY IF EXISTS uq_user_medical_conditions_profile_condition
            """
        )

    # Drop unique constraints/indexes for user_daily_training_intentions
    op.execute(
        """
        ALTER TABLE user_daily_training_intentions
        DROP CONSTRAINT IF EXISTS uq_training_intention_profile_date
        """
    )
    with op.get_context().autocommit_block():
        op.execute(
            """
            DROP INDEX CONCURRENTLY IF EXISTS uq_user_daily_training_intentions_profile_date
            """
        )

    # Drop unique constraints/indexes for body_weight_measurements
    op.execute(
        """
        ALTER TABLE body_weight_measurements
        DROP CONSTRAINT IF EXISTS uq_weight_user_timestamp
        """
    )
    with op.get_context().autocommit_block():
        op.execute(
            """
            DROP INDEX CONCURRENTLY IF EXISTS uq_body_weight_measurements_user_measured_at
            """
        )

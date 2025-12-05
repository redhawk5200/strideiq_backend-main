"""Add injury tracking tables

Revision ID: 20250118_add_injury_tracking
Revises: 20250117_add_coaching_sessions
Create Date: 2025-01-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250118_add_injury_tracking'
down_revision = '20250117_add_coaching_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_injuries table
    op.create_table(
        'user_injuries',
        sa.Column('id', sa.String(length=25), nullable=False),
        sa.Column('user_id', sa.String(length=25), nullable=False),

        # Injury Details
        sa.Column('injury_type', sa.String(length=100), nullable=False),
        sa.Column('affected_area', sa.String(length=100), nullable=False),
        sa.Column('severity_level', sa.String(length=20), nullable=False),

        # Pain Tracking
        sa.Column('initial_pain_level', sa.Integer(), nullable=True),
        sa.Column('current_pain_level', sa.Integer(), nullable=True),

        # Timeline
        sa.Column('injury_date', sa.DateTime(), nullable=False),
        sa.Column('reported_date', sa.DateTime(), nullable=False),
        sa.Column('expected_recovery_date', sa.DateTime(), nullable=True),
        sa.Column('actual_recovery_date', sa.DateTime(), nullable=True),

        # Status
        sa.Column('status', sa.String(length=20), nullable=False),

        # Description and Symptoms
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('symptoms', sa.Text(), nullable=True),
        sa.Column('treatment_plan', sa.Text(), nullable=True),

        # Activity Restrictions (JSON)
        sa.Column('activity_restrictions', postgresql.JSON(astext_type=sa.Text()), nullable=True),

        # Tracking Notes
        sa.Column('recovery_notes', sa.Text(), nullable=True),
        sa.Column('last_update_date', sa.DateTime(), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for user_injuries
    op.create_index('idx_user_injuries_user_id', 'user_injuries', ['user_id'])
    op.create_index('idx_user_injuries_status', 'user_injuries', ['status'])
    op.create_index('idx_user_injuries_date', 'user_injuries', ['injury_date'])
    op.create_index('idx_user_injuries_status_user', 'user_injuries', ['user_id', 'status'])

    # Create injury_updates table
    op.create_table(
        'injury_updates',
        sa.Column('id', sa.String(length=25), nullable=False),
        sa.Column('injury_id', sa.String(length=25), nullable=False),
        sa.Column('user_id', sa.String(length=25), nullable=False),

        # Update Details
        sa.Column('update_date', sa.DateTime(), nullable=False),
        sa.Column('pain_level', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),

        # Progress Notes
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('improvement_level', sa.String(length=20), nullable=True),

        # Activities (JSON)
        sa.Column('activities_performed', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('pain_triggers', postgresql.JSON(astext_type=sa.Text()), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(['injury_id'], ['user_injuries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for injury_updates
    op.create_index('idx_injury_updates_injury_id', 'injury_updates', ['injury_id'])
    op.create_index('idx_injury_updates_user_id', 'injury_updates', ['user_id'])
    op.create_index('idx_injury_updates_date', 'injury_updates', ['update_date'])
    op.create_index('idx_injury_updates_injury_date', 'injury_updates', ['injury_id', 'update_date'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_injury_updates_injury_date', table_name='injury_updates')
    op.drop_index('idx_injury_updates_date', table_name='injury_updates')
    op.drop_index('idx_injury_updates_user_id', table_name='injury_updates')
    op.drop_index('idx_injury_updates_injury_id', table_name='injury_updates')

    # Drop injury_updates table
    op.drop_table('injury_updates')

    # Drop indexes for user_injuries
    op.drop_index('idx_user_injuries_status_user', table_name='user_injuries')
    op.drop_index('idx_user_injuries_date', table_name='user_injuries')
    op.drop_index('idx_user_injuries_status', table_name='user_injuries')
    op.drop_index('idx_user_injuries_user_id', table_name='user_injuries')

    # Drop user_injuries table
    op.drop_table('user_injuries')

"""add coaching recommendations table

Revision ID: 20250112_add_coaching_rec
Revises: 20241101_add_unique_indexes
Create Date: 2025-01-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250112_add_coaching_rec"
down_revision = "20241101_add_unique_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create coaching_recommendations table (using String for status to avoid enum issues)
    op.create_table(
        'coaching_recommendations',
        sa.Column('id', sa.String(25), primary_key=True, index=True),
        sa.Column('user_id', sa.String(25), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('recommendation_date', sa.DateTime(), nullable=False, index=True),
        sa.Column('workout_type', sa.String(50), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('intensity_zone', sa.String(20), nullable=True),
        sa.Column('heart_rate_range', sa.String(20), nullable=True),
        sa.Column('todays_training', sa.Text(), nullable=True),
        sa.Column('nutrition_fueling', sa.Text(), nullable=True),
        sa.Column('recovery_protocol', sa.Text(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('actual_workout_id', sa.String(25), sa.ForeignKey('workout_sessions.id'), nullable=True),
        sa.Column('compliance_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )

    # Create indexes
    op.create_index('ix_coaching_rec_user_date', 'coaching_recommendations', ['user_id', 'recommendation_date'])
    op.create_index('ix_coaching_rec_user_status', 'coaching_recommendations', ['user_id', 'status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_coaching_rec_user_status', table_name='coaching_recommendations')
    op.drop_index('ix_coaching_rec_user_date', table_name='coaching_recommendations')

    # Drop table
    op.drop_table('coaching_recommendations')

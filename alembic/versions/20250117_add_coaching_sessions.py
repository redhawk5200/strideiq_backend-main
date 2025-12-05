"""add coaching sessions table

Revision ID: 20250117_add_coaching_sessions
Revises: 20250112_add_coaching_rec
Create Date: 2025-01-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250117_add_coaching_sessions"
down_revision = "20250112_add_coaching_rec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create coaching_sessions table
    op.create_table(
        'coaching_sessions',
        sa.Column('id', sa.String(25), primary_key=True, index=True),
        sa.Column('user_id', sa.String(25), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, index=True),
        sa.Column('last_active_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # Create composite index
    op.create_index('ix_coaching_session_user_started', 'coaching_sessions', ['user_id', 'started_at'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_coaching_session_user_started', table_name='coaching_sessions')

    # Drop table
    op.drop_table('coaching_sessions')

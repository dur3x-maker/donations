"""add password reset and archived campaigns

Revision ID: 0023_password_reset
Revises: 0022_telegram_moderation
"""

import sqlalchemy as sa
from alembic import op


revision = "0023_password_reset"
down_revision = "0022_telegram_moderation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(128)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires_at TIMESTAMP WITH TIME ZONE")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_password_reset_token ON users (password_reset_token)")

    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE campaign_lifecycle_status ADD VALUE IF NOT EXISTS 'ARCHIVED'")

    op.execute("DROP INDEX IF EXISTS uq_campaigns_owner_unfinished")
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_campaigns_owner_unfinished "
            "ON campaigns (owner_id) "
            "WHERE is_active IS TRUE AND status IN "
            "('ACTIVE', 'PENDING_REVIEW', 'REVISION_REQUIRED', 'GOAL_REACHED', 'AWAITING_REPORT')"
        )
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_password_reset_token")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_reset_expires_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_reset_token")

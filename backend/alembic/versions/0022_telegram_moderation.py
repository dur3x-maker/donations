"""add telegram high value moderation

Revision ID: 0022_telegram_moderation
Revises: 0021_email_verification
"""

import sqlalchemy as sa
from alembic import op


revision = "0022_telegram_moderation"
down_revision = "0021_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE campaign_lifecycle_status ADD VALUE IF NOT EXISTS 'REVISION_REQUIRED'")
        op.execute("ALTER TYPE campaign_lifecycle_status ADD VALUE IF NOT EXISTS 'REJECTED'")
        op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'campaign_moderation'")

    op.execute("DROP INDEX IF EXISTS uq_campaigns_owner_unfinished")
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_campaigns_owner_unfinished "
            "ON campaigns (owner_id) "
            "WHERE is_active IS TRUE AND status IN "
            "('ACTIVE', 'PENDING_REVIEW', 'REVISION_REQUIRED', 'GOAL_REACHED', 'AWAITING_REPORT')"
        )
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telegram_moderation_sessions (
            id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            campaign_id UUID NOT NULL,
            chat_id VARCHAR(64) NOT NULL,
            message_id INTEGER NOT NULL,
            admin_telegram_id VARCHAR(64) NOT NULL,
            admin_name VARCHAR(160) NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_telegram_moderation_sessions_campaign_id ON telegram_moderation_sessions (campaign_id)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_telegram_moderation_sessions_admin_telegram_id "
        "ON telegram_moderation_sessions (admin_telegram_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_telegram_moderation_sessions_admin_telegram_id")
    op.execute("DROP INDEX IF EXISTS ix_telegram_moderation_sessions_campaign_id")
    op.execute("DROP TABLE IF EXISTS telegram_moderation_sessions")
    op.execute("DROP INDEX IF EXISTS uq_campaigns_owner_unfinished")
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_campaigns_owner_unfinished "
            "ON campaigns (owner_id) "
            "WHERE is_active IS TRUE AND status IN ('ACTIVE', 'PENDING_REVIEW', 'GOAL_REACHED', 'AWAITING_REPORT')"
        )
    )

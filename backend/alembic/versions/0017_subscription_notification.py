"""add subscription notification type

Revision ID: 0017_subscription_notification
Revises: 0016_report_reminders
"""

from alembic import op


revision = "0017_subscription_notification"
down_revision = "0016_report_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'campaign_subscription_created'"
    )


def downgrade() -> None:
    pass

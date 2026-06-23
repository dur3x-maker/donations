"""report reminders and overdue state

Revision ID: 0016_report_reminders
Revises: 0015_campaign_owner_fk
Create Date: 2026-06-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_report_reminders"
down_revision: str | None = "0015_campaign_owner_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("report_reminder_30_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaigns", sa.Column("report_reminder_60_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaigns", sa.Column("report_reminder_90_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaigns", sa.Column("report_overdue", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'campaign_report_reminder'")
    op.alter_column("campaigns", "report_overdue", server_default=None)


def downgrade() -> None:
    op.drop_column("campaigns", "report_overdue")
    op.drop_column("campaigns", "report_reminder_90_sent_at")
    op.drop_column("campaigns", "report_reminder_60_sent_at")
    op.drop_column("campaigns", "report_reminder_30_sent_at")

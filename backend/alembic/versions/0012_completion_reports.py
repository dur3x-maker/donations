"""completion reports

Revision ID: 0012_completion_reports
Revises: 0011_donor_reputation
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_completion_reports"
down_revision: str | None = "0011_donor_reputation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    lifecycle_status = postgresql.ENUM("ACTIVE", "GOAL_REACHED", "AWAITING_REPORT", "COMPLETED", name="campaign_lifecycle_status")
    lifecycle_status.create(op.get_bind(), checkfirst=True)

    op.add_column("campaigns", sa.Column("status", lifecycle_status, nullable=False, server_default="ACTIVE"))
    op.add_column("campaigns", sa.Column("report_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaigns", sa.Column("report_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_campaigns_status"), "campaigns", ["status"], unique=False)

    op.execute(
        """
        UPDATE campaigns
        SET status = CASE
            WHEN has_completion_report IS TRUE THEN 'COMPLETED'::campaign_lifecycle_status
            WHEN current_amount >= target_amount THEN 'AWAITING_REPORT'::campaign_lifecycle_status
            ELSE 'ACTIVE'::campaign_lifecycle_status
        END,
        report_requested_at = CASE
            WHEN has_completion_report IS FALSE AND current_amount >= target_amount THEN goal_reached_notified_at
            ELSE report_requested_at
        END
        """
    )
    op.alter_column("campaigns", "status", server_default=None)

    op.create_table(
        "campaign_completion_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gratitude_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id"),
    )
    op.create_index(op.f("ix_campaign_completion_reports_campaign_id"), "campaign_completion_reports", ["campaign_id"], unique=False)

    op.create_table(
        "campaign_completion_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["campaign_completion_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_campaign_completion_photos_report_id"), "campaign_completion_photos", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_completion_photos_report_id"), table_name="campaign_completion_photos")
    op.drop_table("campaign_completion_photos")
    op.drop_index(op.f("ix_campaign_completion_reports_campaign_id"), table_name="campaign_completion_reports")
    op.drop_table("campaign_completion_reports")
    op.drop_index(op.f("ix_campaigns_status"), table_name="campaigns")
    op.drop_column("campaigns", "report_completed_at")
    op.drop_column("campaigns", "report_requested_at")
    op.drop_column("campaigns", "status")
    postgresql.ENUM(name="campaign_lifecycle_status").drop(op.get_bind(), checkfirst=True)

"""moderation foundation

Revision ID: 0007_moderation_foundation
Revises: 0006_social_activity
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_moderation_foundation"
down_revision: str | None = "0006_social_activity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    user_role = postgresql.ENUM("user", "moderator", "admin", name="user_role", create_type=False)
    report_status = postgresql.ENUM("pending", "reviewed", "dismissed", "action_taken", name="report_status", create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)
    report_status.create(op.get_bind(), checkfirst=True)

    op.add_column("users", sa.Column("role", user_role, nullable=False, server_default="user"))
    op.alter_column("users", "role", server_default=None)

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", report_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_campaign_id"), "reports", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_reports_reporter_user_id"), "reports", ["reporter_user_id"], unique=False)
    op.create_index(op.f("ix_reports_status"), "reports", ["status"], unique=False)

    op.create_table(
        "suspicious_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_suspicious_flags_campaign_id"), "suspicious_flags", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_suspicious_flags_type"), "suspicious_flags", ["type"], unique=False)
    op.create_index(op.f("ix_suspicious_flags_user_id"), "suspicious_flags", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_suspicious_flags_user_id"), table_name="suspicious_flags")
    op.drop_index(op.f("ix_suspicious_flags_type"), table_name="suspicious_flags")
    op.drop_index(op.f("ix_suspicious_flags_campaign_id"), table_name="suspicious_flags")
    op.drop_table("suspicious_flags")
    op.drop_index(op.f("ix_reports_status"), table_name="reports")
    op.drop_index(op.f("ix_reports_reporter_user_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_campaign_id"), table_name="reports")
    op.drop_table("reports")
    op.drop_column("users", "role")
    postgresql.ENUM(name="report_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)

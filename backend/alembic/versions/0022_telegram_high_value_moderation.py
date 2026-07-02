"""add telegram high value moderation

Revision ID: 0022_telegram_high_value_moderation
Revises: 0021_email_verification_token
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0022_telegram_high_value_moderation"
down_revision = "0021_email_verification_token"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE campaign_lifecycle_status ADD VALUE IF NOT EXISTS 'REVISION_REQUIRED'")
        op.execute("ALTER TYPE campaign_lifecycle_status ADD VALUE IF NOT EXISTS 'REJECTED'")
        op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'campaign_moderation'")

    op.drop_index("uq_campaigns_owner_unfinished", table_name="campaigns")
    op.create_index(
        "uq_campaigns_owner_unfinished",
        "campaigns",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_active IS TRUE AND status IN "
            "('ACTIVE', 'PENDING_REVIEW', 'REVISION_REQUIRED', 'GOAL_REACHED', 'AWAITING_REPORT')"
        ),
    )

    op.create_table(
        "telegram_moderation_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chat_id", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("admin_telegram_id", sa.String(length=64), nullable=False),
        sa.Column("admin_name", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_telegram_moderation_sessions_campaign_id"), "telegram_moderation_sessions", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_telegram_moderation_sessions_admin_telegram_id"), "telegram_moderation_sessions", ["admin_telegram_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_telegram_moderation_sessions_admin_telegram_id"), table_name="telegram_moderation_sessions")
    op.drop_index(op.f("ix_telegram_moderation_sessions_campaign_id"), table_name="telegram_moderation_sessions")
    op.drop_table("telegram_moderation_sessions")
    op.drop_index("uq_campaigns_owner_unfinished", table_name="campaigns")
    op.create_index(
        "uq_campaigns_owner_unfinished",
        "campaigns",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_active IS TRUE AND status IN ('ACTIVE', 'PENDING_REVIEW', 'GOAL_REACHED', 'AWAITING_REPORT')"
        ),
    )

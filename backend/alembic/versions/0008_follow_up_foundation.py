"""follow up foundation

Revision ID: 0008_follow_up_foundation
Revises: 0007_moderation_foundation
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_follow_up_foundation"
down_revision: str | None = "0007_moderation_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for value in (
        "campaign_goal_reached",
        "campaign_report_published",
        "campaign_photos_added",
        "campaign_author_update_created",
    ):
        op.execute(f"ALTER TYPE notification_type ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column("campaigns", sa.Column("goal_reached_notified_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "campaign_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("muted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "campaign_id", name="uq_campaign_subscriptions_user_campaign"),
    )
    op.create_index(op.f("ix_campaign_subscriptions_campaign_id"), "campaign_subscriptions", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_campaign_subscriptions_user_id"), "campaign_subscriptions", ["user_id"], unique=False)

    op.add_column("notifications", sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("action_url", sa.String(length=1024), nullable=True))
    op.create_foreign_key("fk_notifications_campaign_id_campaigns", "notifications", "campaigns", ["campaign_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_notifications_campaign_id"), "notifications", ["campaign_id"], unique=False)
    op.create_index("ix_notifications_user_created_at", "notifications", ["user_id", "created_at"], unique=False)

    op.alter_column("campaign_subscriptions", "is_active", server_default=None)
    op.alter_column("campaign_subscriptions", "muted", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_notifications_user_created_at", table_name="notifications")
    op.drop_index(op.f("ix_notifications_campaign_id"), table_name="notifications")
    op.drop_constraint("fk_notifications_campaign_id_campaigns", "notifications", type_="foreignkey")
    op.drop_column("notifications", "action_url")
    op.drop_column("notifications", "campaign_id")

    op.drop_index(op.f("ix_campaign_subscriptions_user_id"), table_name="campaign_subscriptions")
    op.drop_index(op.f("ix_campaign_subscriptions_campaign_id"), table_name="campaign_subscriptions")
    op.drop_table("campaign_subscriptions")

    op.drop_column("campaigns", "goal_reached_notified_at")

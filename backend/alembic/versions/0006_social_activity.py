"""social activity

Revision ID: 0006_social_activity
Revises: 0005_payment_preparation
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_social_activity"
down_revision: str | None = "0005_payment_preparation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    activity_type = postgresql.ENUM(
        "campaign_created",
        "donation_made",
        "campaign_completed",
        "unlock_achieved",
        name="activity_type",
        create_type=False,
    )
    notification_type = postgresql.ENUM(
        "donation_received",
        "campaign_funded",
        "unlock_achieved",
        name="notification_type",
        create_type=False,
    )
    activity_type.create(op.get_bind(), checkfirst=True)
    notification_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", activity_type, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activities_actor_user_id"), "activities", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_activities_campaign_id"), "activities", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_activities_type"), "activities", ["type"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"], unique=False)
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_is_read"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_activities_type"), table_name="activities")
    op.drop_index(op.f("ix_activities_campaign_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_actor_user_id"), table_name="activities")
    op.drop_table("activities")
    postgresql.ENUM(name="notification_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="activity_type").drop(op.get_bind(), checkfirst=True)

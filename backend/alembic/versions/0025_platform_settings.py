"""add featured campaign setting

Revision ID: 0025_platform_settings
Revises: 0024_contact_requests
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0025_platform_settings"
down_revision: str | None = "0024_contact_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("featured_campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["featured_campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="ck_platform_settings_singleton"),
    )
    op.add_column(
        "telegram_moderation_sessions",
        sa.Column("state", sa.String(length=32), nullable=False, server_default="revision_reason"),
    )
    op.add_column(
        "telegram_moderation_sessions",
        sa.Column("requested_username", sa.String(length=24), nullable=True),
    )
    op.alter_column("telegram_moderation_sessions", "campaign_id", existing_type=postgresql.UUID(), nullable=True)
    op.alter_column("telegram_moderation_sessions", "state", server_default=None)


def downgrade() -> None:
    op.execute("DELETE FROM telegram_moderation_sessions WHERE campaign_id IS NULL")
    op.alter_column("telegram_moderation_sessions", "campaign_id", existing_type=postgresql.UUID(), nullable=False)
    op.drop_column("telegram_moderation_sessions", "requested_username")
    op.drop_column("telegram_moderation_sessions", "state")
    op.drop_table("platform_settings")

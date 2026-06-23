"""campaign updates

Revision ID: 0009_campaign_updates
Revises: 0008_follow_up_foundation
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_campaign_updates"
down_revision: str | None = "0008_follow_up_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "campaign_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_updates_campaign_id", "campaign_updates", ["campaign_id"], unique=False)
    op.create_index("ix_campaign_updates_created_at", "campaign_updates", ["created_at"], unique=False)

    op.create_table(
        "campaign_update_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("update_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["update_id"], ["campaign_updates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_campaign_update_photos_update_id"), "campaign_update_photos", ["update_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_update_photos_update_id"), table_name="campaign_update_photos")
    op.drop_table("campaign_update_photos")
    op.drop_index("ix_campaign_updates_created_at", table_name="campaign_updates")
    op.drop_index("ix_campaign_updates_campaign_id", table_name="campaign_updates")
    op.drop_table("campaign_updates")

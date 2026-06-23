"""campaign mvp

Revision ID: 0003_campaign_mvp
Revises: 0002_auth_mvp
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_campaign_mvp"
down_revision: str | None = "0002_auth_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("category", sa.String(length=32), nullable=False, server_default="other"))
    op.add_column("campaigns", sa.Column("cover_image_url", sa.String(length=1024), nullable=True))
    op.add_column("campaigns", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("campaigns", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.execute("UPDATE campaigns SET cover_image_url = image_url WHERE image_url IS NOT NULL")
    op.execute("UPDATE campaigns SET is_active = true WHERE status = 'active'")

    op.drop_column("campaigns", "image_url")
    op.drop_column("campaigns", "status")
    op.drop_column("contributions", "donor_name")
    op.drop_column("contributions", "payment_status")
    op.drop_column("contributions", "confirmed_at")

    op.alter_column("campaigns", "owner_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("campaigns", "category", server_default=None)
    op.alter_column("campaigns", "is_verified", server_default=None)
    op.alter_column("campaigns", "is_active", server_default=None)
    op.create_index(op.f("ix_campaigns_owner_id"), "campaigns", ["owner_id"], unique=False)
    op.create_index("ix_campaigns_created_at", "campaigns", ["created_at"], unique=False)

    sa.Enum(name="payment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="campaign_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    campaign_status = sa.Enum("draft", "active", "completed", "blocked", name="campaign_status")
    payment_status = sa.Enum("pending", "confirmed", "failed", name="payment_status")
    campaign_status.create(op.get_bind(), checkfirst=True)
    payment_status.create(op.get_bind(), checkfirst=True)

    op.drop_index("ix_campaigns_created_at", table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_owner_id"), table_name="campaigns")
    op.add_column("contributions", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("contributions", sa.Column("payment_status", payment_status, nullable=False, server_default="confirmed"))
    op.add_column("contributions", sa.Column("donor_name", sa.String(length=120), nullable=True))
    op.add_column("campaigns", sa.Column("status", campaign_status, nullable=False, server_default="active"))
    op.add_column("campaigns", sa.Column("image_url", sa.String(length=1024), nullable=True))
    op.execute("UPDATE campaigns SET image_url = cover_image_url WHERE cover_image_url IS NOT NULL")
    op.alter_column("campaigns", "owner_id", existing_type=sa.UUID(), nullable=True)
    op.drop_column("campaigns", "is_active")
    op.drop_column("campaigns", "is_verified")
    op.drop_column("campaigns", "cover_image_url")
    op.drop_column("campaigns", "category")

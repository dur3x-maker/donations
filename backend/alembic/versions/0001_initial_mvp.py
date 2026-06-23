"""initial mvp tables

Revision ID: 0001_initial_mvp
Revises:
Create Date: 2026-05-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_mvp"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    campaign_status = postgresql.ENUM("draft", "active", "completed", "blocked", name="campaign_status", create_type=False)
    payment_status = postgresql.ENUM("pending", "confirmed", "failed", name="payment_status", create_type=False)
    campaign_status.create(op.get_bind(), checkfirst=True)
    payment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("status", campaign_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("anonymous_token", sa.String(length=128), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("donor_name", sa.String(length=120), nullable=True),
        sa.Column("payment_status", payment_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contributions_anonymous_token"), "contributions", ["anonymous_token"], unique=False)
    op.create_index(op.f("ix_contributions_campaign_id"), "contributions", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_contributions_user_id"), "contributions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_contributions_user_id"), table_name="contributions")
    op.drop_index(op.f("ix_contributions_campaign_id"), table_name="contributions")
    op.drop_index(op.f("ix_contributions_anonymous_token"), table_name="contributions")
    op.drop_table("contributions")
    op.drop_table("campaigns")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    postgresql.ENUM(name="payment_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="campaign_status").drop(op.get_bind(), checkfirst=True)

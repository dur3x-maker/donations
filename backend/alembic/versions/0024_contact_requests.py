"""store contact requests

Revision ID: 0024_contact_requests
Revises: 0023_password_reset
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0024_contact_requests"
down_revision: str | None = "0023_password_reset"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contact_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("telegram", sa.String(length=33), nullable=True),
        sa.Column("subject", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contact_requests_email"), "contact_requests", ["email"], unique=False)
    op.create_index(op.f("ix_contact_requests_user_id"), "contact_requests", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_contact_requests_user_id"), table_name="contact_requests")
    op.drop_index(op.f("ix_contact_requests_email"), table_name="contact_requests")
    op.drop_table("contact_requests")

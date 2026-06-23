"""auth mvp

Revision ID: 0002_auth_mvp
Revises: 0001_initial_mvp
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_auth_mvp"
down_revision: str | None = "0001_initial_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_DISABLED_PASSWORD_HASH = "legacy-disabled"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=LEGACY_DISABLED_PASSWORD_HASH),
    )
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.execute(
        """
        UPDATE users
        SET email = lower(coalesce(email, id::text || '@legacy.local')),
            username = lower(username)
        """
    )

    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("users", "username", existing_type=sa.String(length=64), type_=sa.String(length=24), nullable=False)
    op.alter_column("users", "password_hash", server_default=None)
    op.alter_column("users", "is_active", server_default=None)
    op.alter_column("users", "is_verified", server_default=None)


def downgrade() -> None:
    op.alter_column("users", "username", existing_type=sa.String(length=24), type_=sa.String(length=64), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)
    op.drop_column("users", "is_verified")
    op.drop_column("users", "is_active")
    op.drop_column("users", "password_hash")

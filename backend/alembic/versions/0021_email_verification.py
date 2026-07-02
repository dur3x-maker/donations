"""add email verification token

Revision ID: 0021_email_verification
Revises: 0020_bank_account_apps
"""

import sqlalchemy as sa
from alembic import op


revision = "0021_email_verification"
down_revision = "0020_bank_account_apps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("verification_token", sa.String(length=128), nullable=True))
    op.create_index(op.f("ix_users_verification_token"), "users", ["verification_token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_verification_token"), table_name="users")
    op.drop_column("users", "verification_token")

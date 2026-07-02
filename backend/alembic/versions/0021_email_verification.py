"""add email verification token

Revision ID: 0021_email_verification
Revises: 0020_bank_account_apps
"""

from alembic import op


revision = "0021_email_verification"
down_revision = "0020_bank_account_apps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(128)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_verification_token ON users (verification_token)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_verification_token")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS verification_token")

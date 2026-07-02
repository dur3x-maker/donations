"""add user profile fields

Revision ID: 0018_user_profile_fields
Revises: 0017_subscription_notification
"""

from alembic import op


revision = "0018_user_profile_fields"
down_revision = "0017_subscription_notification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(80)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(80)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio VARCHAR(250)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(80)")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS city")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS bio")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_name")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS first_name")

"""add user profile fields

Revision ID: 0018_user_profile_fields
Revises: 0017_subscription_notification
"""

import sqlalchemy as sa
from alembic import op


revision = "0018_user_profile_fields"
down_revision = "0017_subscription_notification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("bio", sa.String(length=250), nullable=True))
    op.add_column("users", sa.Column("city", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "city")
    op.drop_column("users", "bio")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")

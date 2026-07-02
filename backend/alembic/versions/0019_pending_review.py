"""add pending review campaign status

Revision ID: 0019_pending_review
Revises: 0018_user_profile_fields
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_pending_review"
down_revision = "0018_user_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE campaign_lifecycle_status ADD VALUE IF NOT EXISTS 'PENDING_REVIEW'")
    op.drop_index("uq_campaigns_owner_unfinished", table_name="campaigns")
    op.create_index(
        "uq_campaigns_owner_unfinished",
        "campaigns",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_active IS TRUE AND status IN "
            "('ACTIVE', 'PENDING_REVIEW', 'GOAL_REACHED', 'AWAITING_REPORT')"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_campaigns_owner_unfinished", table_name="campaigns")
    op.create_index(
        "uq_campaigns_owner_unfinished",
        "campaigns",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE AND status IN ('ACTIVE', 'GOAL_REACHED', 'AWAITING_REPORT')"),
    )

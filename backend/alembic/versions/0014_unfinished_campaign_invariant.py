"""enforce one unfinished campaign per owner

Revision ID: 0014_unfinished_campaign
Revises: 0013_patron_circle
Create Date: 2026-06-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_unfinished_campaign"
down_revision: str | None = "0013_patron_circle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_campaigns_owner_unfinished",
        "campaigns",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_active IS TRUE AND status IN ('ACTIVE', 'GOAL_REACHED', 'AWAITING_REPORT')"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_campaigns_owner_unfinished", table_name="campaigns")

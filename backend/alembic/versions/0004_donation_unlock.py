"""donation unlock

Revision ID: 0004_donation_unlock
Revises: 0003_campaign_mvp
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_donation_unlock"
down_revision: str | None = "0003_campaign_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    contribution_status = sa.Enum("pending", "confirmed", "rejected", name="contribution_status")
    contribution_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "contributions",
        sa.Column("status", contribution_status, nullable=False, server_default="confirmed"),
    )
    op.alter_column("contributions", "status", server_default=None)


def downgrade() -> None:
    op.drop_column("contributions", "status")
    sa.Enum(name="contribution_status").drop(op.get_bind(), checkfirst=True)

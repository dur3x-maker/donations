"""author reputation foundation

Revision ID: 0010_author_reputation
Revises: 0009_campaign_updates
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_author_reputation"
down_revision: str | None = "0009_campaign_updates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("has_completion_report", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("campaigns", "has_completion_report", server_default=None)


def downgrade() -> None:
    op.drop_column("campaigns", "has_completion_report")

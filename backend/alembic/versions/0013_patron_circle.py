"""patron circle

Revision ID: 0013_patron_circle
Revises: 0012_completion_reports
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_patron_circle"
down_revision: str | None = "0012_completion_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'patron_unlocked'")
    op.add_column("users", sa.Column("patron_since", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_users_patron_since"), "users", ["patron_since"], unique=False)

    op.execute(
        """
        WITH ordered_contributions AS (
            SELECT
                contributions.user_id,
                contributions.created_at,
                row_number() OVER (
                    PARTITION BY contributions.user_id
                    ORDER BY contributions.created_at, contributions.id
                ) AS contribution_number
            FROM contributions
            JOIN payments ON payments.contribution_id = contributions.id
            JOIN campaigns ON campaigns.id = contributions.campaign_id
            WHERE contributions.user_id IS NOT NULL
              AND contributions.status = 'confirmed'
              AND payments.status = 'succeeded'
              AND contributions.amount > 0
              AND campaigns.owner_id != contributions.user_id
        )
        UPDATE users
        SET patron_since = ordered_contributions.created_at
        FROM ordered_contributions
        WHERE users.id = ordered_contributions.user_id
          AND users.patron_since IS NULL
          AND ordered_contributions.contribution_number = 50
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_patron_since"), table_name="users")
    op.drop_column("users", "patron_since")

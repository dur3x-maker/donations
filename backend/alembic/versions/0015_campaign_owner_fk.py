"""align campaign owner foreign key

Revision ID: 0015_campaign_owner_fk
Revises: 0014_unfinished_campaign
Create Date: 2026-06-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015_campaign_owner_fk"
down_revision: str | None = "0014_unfinished_campaign"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("campaigns_owner_id_fkey", "campaigns", type_="foreignkey")
    op.create_foreign_key(
        "campaigns_owner_id_fkey",
        "campaigns",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("campaigns_owner_id_fkey", "campaigns", type_="foreignkey")
    op.create_foreign_key(
        "campaigns_owner_id_fkey",
        "campaigns",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )

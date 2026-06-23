"""donor reputation

Revision ID: 0011_donor_reputation
Revises: 0010_author_reputation
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_donor_reputation"
down_revision: str | None = "0010_author_reputation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'achievement_unlocked'")

    op.create_table(
        "user_achievements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("achievement_code", sa.String(length=80), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "achievement_code", name="uq_user_achievements_user_code"),
    )
    op.create_index(op.f("ix_user_achievements_user_id"), "user_achievements", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_achievements_unlocked_at"), "user_achievements", ["unlocked_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_achievements_unlocked_at"), table_name="user_achievements")
    op.drop_index(op.f("ix_user_achievements_user_id"), table_name="user_achievements")
    op.drop_table("user_achievements")

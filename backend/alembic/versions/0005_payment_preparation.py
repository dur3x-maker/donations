"""payment preparation

Revision ID: 0005_payment_preparation
Revises: 0004_donation_unlock
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_payment_preparation"
down_revision: str | None = "0004_donation_unlock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    payment_status = postgresql.ENUM("pending", "succeeded", "failed", "canceled", name="payment_status", create_type=False)
    payment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contribution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_payment_id", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contribution_id"], ["contributions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_contribution_id"), "payments", ["contribution_id"], unique=True)

    op.execute(
        """
        INSERT INTO payments (
            id,
            contribution_id,
            provider,
            external_payment_id,
            amount,
            currency,
            status,
            confirmed_at,
            metadata_json,
            created_at
        )
        SELECT
            id,
            id,
            'mock',
            NULL,
            amount,
            'RUB',
            CASE
                WHEN status = 'confirmed' THEN 'succeeded'::payment_status
                WHEN status = 'rejected' THEN 'failed'::payment_status
                ELSE 'pending'::payment_status
            END,
            CASE WHEN status = 'confirmed' THEN created_at ELSE NULL END,
            '{"backfilled": true}'::json,
            created_at
        FROM contributions
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_contribution_id"), table_name="payments")
    op.drop_table("payments")
    postgresql.ENUM(name="payment_status").drop(op.get_bind(), checkfirst=True)

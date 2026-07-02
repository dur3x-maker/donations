"""add bank account applications

Revision ID: 0020_bank_account_applications
Revises: 0019_pending_review_campaign_status
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0020_bank_account_applications"
down_revision = "0019_pending_review_campaign_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status_enum = postgresql.ENUM("PENDING", "APPROVED", "REJECTED", name="bank_account_application_status")
    status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "bank_account_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bank_account_applications_user_id"), "bank_account_applications", ["user_id"], unique=True)
    op.create_index(op.f("ix_bank_account_applications_status"), "bank_account_applications", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bank_account_applications_status"), table_name="bank_account_applications")
    op.drop_index(op.f("ix_bank_account_applications_user_id"), table_name="bank_account_applications")
    op.drop_table("bank_account_applications")
    postgresql.ENUM(name="bank_account_application_status").drop(op.get_bind(), checkfirst=True)

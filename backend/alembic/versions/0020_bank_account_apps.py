"""add bank account applications

Revision ID: 0020_bank_account_apps
Revises: 0019_pending_review
"""

from alembic import op


revision = "0020_bank_account_apps"
down_revision = "0019_pending_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE bank_account_application_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bank_account_applications (
            id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            user_id UUID NOT NULL,
            status bank_account_application_status NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_bank_account_applications_user_id ON bank_account_applications (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bank_account_applications_status ON bank_account_applications (status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bank_account_applications_status")
    op.execute("DROP INDEX IF EXISTS ix_bank_account_applications_user_id")
    op.execute("DROP TABLE IF EXISTS bank_account_applications")
    op.execute("DROP TYPE IF EXISTS bank_account_application_status")

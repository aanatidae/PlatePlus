"""Designate one simulated toll account per user as primary."""
# ruff: noqa: I001

import sqlalchemy as sa
from alembic import op


revision = "20260902_0002"
down_revision = "20260901_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE accounts
        SET is_primary = true
        WHERE id IN (
            SELECT DISTINCT ON (user_id) id
            FROM accounts
            ORDER BY user_id, created_at, id
        )
        """
    )
    op.create_index(
        "uq_accounts_one_primary_per_user",
        "accounts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_accounts_one_primary_per_user", table_name="accounts")
    op.drop_column("accounts", "is_primary")

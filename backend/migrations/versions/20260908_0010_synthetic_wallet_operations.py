"""Add simulated wallet, payment-notification, and recognition-review support."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260908_0010"
down_revision = "20260907_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("opening_balance", sa.Numeric(12, 2), nullable=True))
    op.execute("UPDATE accounts SET opening_balance = balance WHERE opening_balance IS NULL")
    op.alter_column("accounts", "opening_balance", nullable=False, server_default="0.00")
    op.add_column("detection_records", sa.Column("review_status", sa.String(24), nullable=False, server_default="not_required"))
    op.add_column("detection_records", sa.Column("review_note", sa.String(255), nullable=True))
    op.add_column("detection_records", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_detection_records_review_status", "detection_records", ["review_status"])
    op.add_column("toll_transactions", sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("toll_transactions", sa.Column("reversal_reason", sa.String(255), nullable=True))
    op.create_table(
        "wallet_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("toll_transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MYR"),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount >= 0", name="ck_wallet_ledger_amount_nonnegative"),
        sa.CheckConstraint("currency = 'MYR'", name="ck_wallet_ledger_currency_myr"),
    )
    op.create_index("ix_wallet_ledger_entries_account_id", "wallet_ledger_entries", ["account_id"])
    op.create_index("ix_wallet_ledger_entries_transaction_id", "wallet_ledger_entries", ["transaction_id"])
    op.create_index("ix_wallet_ledger_entries_entry_type", "wallet_ledger_entries", ["entry_type"])
    op.create_table(
        "payment_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("toll_transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notification_type", sa.String(32), nullable=False),
        sa.Column("message", sa.String(255), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payment_notifications_user_id", "payment_notifications", ["user_id"])
    op.create_index("ix_payment_notifications_transaction_id", "payment_notifications", ["transaction_id"])
    op.create_index("ix_payment_notifications_notification_type", "payment_notifications", ["notification_type"])


def downgrade() -> None:
    for table, index in (
        ("payment_notifications", "ix_payment_notifications_notification_type"),
        ("payment_notifications", "ix_payment_notifications_transaction_id"),
        ("payment_notifications", "ix_payment_notifications_user_id"),
        ("wallet_ledger_entries", "ix_wallet_ledger_entries_entry_type"),
        ("wallet_ledger_entries", "ix_wallet_ledger_entries_transaction_id"),
        ("wallet_ledger_entries", "ix_wallet_ledger_entries_account_id"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("payment_notifications")
    op.drop_table("wallet_ledger_entries")
    op.drop_column("toll_transactions", "reversal_reason")
    op.drop_column("toll_transactions", "reversed_at")
    op.drop_index("ix_detection_records_review_status", table_name="detection_records")
    op.drop_column("detection_records", "reviewed_at")
    op.drop_column("detection_records", "review_note")
    op.drop_column("detection_records", "review_status")
    op.drop_column("accounts", "opening_balance")

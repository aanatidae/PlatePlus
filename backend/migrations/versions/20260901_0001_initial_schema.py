"""Create the initial backend and database schema."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260901_0001"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    uuid_pk = lambda: sa.Column(
        "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )

    op.create_table(
        "admins",
        uuid_pk(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.UniqueConstraint("email", name="uq_admins_email"),
    )
    op.create_index("ix_admins_email", "admins", ["email"])

    op.create_table(
        "users",
        uuid_pk(),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "accounts",
        uuid_pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MYR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.CheckConstraint("balance >= 0", name="ck_accounts_balance_nonnegative"),
        sa.CheckConstraint("currency = 'MYR'", name="ck_accounts_currency_myr"),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    op.create_table(
        "vehicles",
        uuid_pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plate_number", sa.String(16), nullable=False),
        sa.Column("make", sa.String(80)),
        sa.Column("model", sa.String(80)),
        sa.Column("color", sa.String(40)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.UniqueConstraint("plate_number", name="uq_vehicles_plate_number"),
    )
    op.create_index("ix_vehicles_user_id", "vehicles", ["user_id"])
    op.create_index("ix_vehicles_plate_number", "vehicles", ["plate_number"])

    op.create_table(
        "traffic_records",
        uuid_pk(),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vehicle_count", sa.Integer(), nullable=False),
        sa.Column("road_capacity", sa.Integer(), nullable=False),
        sa.Column("congestion_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("congestion_category", sa.String(16), nullable=False),
        sa.Column("scenario", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.CheckConstraint("vehicle_count >= 0", name="ck_traffic_vehicle_count_nonnegative"),
        sa.CheckConstraint("road_capacity > 0", name="ck_traffic_road_capacity_positive"),
        sa.CheckConstraint(
            "congestion_percentage >= 0 AND congestion_percentage <= 100",
            name="ck_traffic_percentage_range",
        ),
    )
    op.create_index("ix_traffic_records_measured_at", "traffic_records", ["measured_at"])
    op.create_index(
        "ix_traffic_records_congestion_category", "traffic_records", ["congestion_category"]
    )

    op.create_table(
        "toll_prices",
        uuid_pk(),
        sa.Column(
            "traffic_record_id", UUID, sa.ForeignKey("traffic_records.id", ondelete="SET NULL")
        ),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(8, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MYR"),
        sa.Column("congestion_category", sa.String(16), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.CheckConstraint("amount >= 0", name="ck_toll_prices_amount_nonnegative"),
        sa.CheckConstraint("currency = 'MYR'", name="ck_toll_prices_currency_myr"),
    )
    op.create_index("ix_toll_prices_traffic_record_id", "toll_prices", ["traffic_record_id"])
    op.create_index("ix_toll_prices_effective_at", "toll_prices", ["effective_at"])

    op.create_table(
        "detection_records",
        uuid_pk(),
        sa.Column("vehicle_id", UUID, sa.ForeignKey("vehicles.id", ondelete="SET NULL")),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_plate_text", sa.String(64)),
        sa.Column("normalized_plate", sa.String(16)),
        sa.Column("detection_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("ocr_confidence", sa.Numeric(5, 4)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="webcam"),
        sa.Column("image_path", sa.Text()),
        sa.Column("crop_path", sa.Text()),
        sa.Column("metadata_json", sa.Text()),
        *timestamps(),
        sa.CheckConstraint(
            "detection_confidence >= 0 AND detection_confidence <= 1",
            name="ck_detection_confidence_range",
        ),
        sa.CheckConstraint(
            "ocr_confidence IS NULL OR (ocr_confidence >= 0 AND ocr_confidence <= 1)",
            name="ck_ocr_confidence_range",
        ),
    )
    op.create_index("ix_detection_records_vehicle_id", "detection_records", ["vehicle_id"])
    op.create_index("ix_detection_records_detected_at", "detection_records", ["detected_at"])
    op.create_index(
        "ix_detection_records_normalized_plate", "detection_records", ["normalized_plate"]
    )
    op.create_index("ix_detection_records_status", "detection_records", ["status"])
    op.create_index(
        "ix_detection_records_plate_detected_at",
        "detection_records",
        ["normalized_plate", "detected_at"],
    )

    op.create_table(
        "toll_transactions",
        uuid_pk(),
        sa.Column("account_id", UUID, sa.ForeignKey("accounts.id", ondelete="SET NULL")),
        sa.Column("vehicle_id", UUID, sa.ForeignKey("vehicles.id", ondelete="SET NULL")),
        sa.Column("toll_price_id", UUID, sa.ForeignKey("toll_prices.id", ondelete="SET NULL")),
        sa.Column(
            "detection_id",
            UUID,
            sa.ForeignKey("detection_records.id", ondelete="SET NULL"),
            unique=True,
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(8, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MYR"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("failure_reason", sa.String(255)),
        sa.Column("balance_after", sa.Numeric(12, 2)),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.CheckConstraint("amount >= 0", name="ck_transactions_amount_nonnegative"),
        sa.CheckConstraint(
            "balance_after IS NULL OR balance_after >= 0",
            name="ck_transactions_balance_nonnegative",
        ),
        sa.CheckConstraint("currency = 'MYR'", name="ck_transactions_currency_myr"),
    )
    for column in ("account_id", "vehicle_id", "toll_price_id", "processed_at", "status"):
        op.create_index(f"ix_toll_transactions_{column}", "toll_transactions", [column])


def downgrade() -> None:
    for table in (
        "toll_transactions",
        "detection_records",
        "toll_prices",
        "traffic_records",
        "vehicles",
        "accounts",
        "users",
        "admins",
    ):
        op.drop_table(table)

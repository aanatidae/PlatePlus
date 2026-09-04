"""Add location ownership to simulated toll operations."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260904_0004"
down_revision = "20260902_0003"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
PENCHALA_LOCATION_ID = "f44f0255-9134-5c7f-9a71-5aaadf7cd095"


def upgrade() -> None:
    op.create_table(
        "toll_locations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("highway_or_route", sa.String(120), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="operational"),
        sa.Column("base_toll", sa.Numeric(8, 2), nullable=False),
        sa.Column("road_capacity", sa.Integer(), nullable=False),
        sa.Column("simulation_profile", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint("code", name="uq_toll_locations_code"),
        sa.CheckConstraint("base_toll >= 0", name="ck_toll_locations_base_toll_nonnegative"),
        sa.CheckConstraint("road_capacity > 0", name="ck_toll_locations_road_capacity_positive"),
    )
    op.create_index("ix_toll_locations_code", "toll_locations", ["code"])

    locations = sa.table(
        "toll_locations",
        sa.column("id", UUID),
        sa.column("code"),
        sa.column("display_name"),
        sa.column("highway_or_route"),
        sa.column("latitude"),
        sa.column("longitude"),
        sa.column("status"),
        sa.column("base_toll"),
        sa.column("road_capacity"),
        sa.column("simulation_profile", postgresql.JSONB()),
    )
    op.bulk_insert(
        locations,
        [
            {
                "id": PENCHALA_LOCATION_ID,
                "code": "PENCHALA",
                "display_name": "Penchala Toll Plaza",
                "highway_or_route": "LDP / E11",
                "latitude": 3.145200,
                "longitude": 101.621700,
                "status": "operational",
                "base_toll": 2.00,
                "road_capacity": 1000,
                "simulation_profile": {
                    "baseline_demand": 0.42,
                    "peak_factor": 1.45,
                    "speed_profile": "urban",
                },
            },
            {
                "id": "07148697-d219-519e-8436-b64d6dd2c8c3",
                "code": "SUNGAI_BESI",
                "display_name": "Sungai Besi Toll Plaza",
                "highway_or_route": "BESRAYA / E9",
                "latitude": 3.072800,
                "longitude": 101.710500,
                "status": "operational",
                "base_toll": 2.40,
                "road_capacity": 1200,
                "simulation_profile": {
                    "baseline_demand": 0.55,
                    "peak_factor": 1.60,
                    "speed_profile": "urban",
                },
            },
            {
                "id": "2c38d3c0-e21e-5a84-9d42-c603849c593f",
                "code": "AYER_KEROH",
                "display_name": "Ayer Keroh Toll Plaza",
                "highway_or_route": "PLUS / E2",
                "latitude": 2.271100,
                "longitude": 102.282400,
                "status": "operational",
                "base_toll": 3.20,
                "road_capacity": 1500,
                "simulation_profile": {
                    "baseline_demand": 0.36,
                    "peak_factor": 1.30,
                    "speed_profile": "intercity",
                },
            },
            {
                "id": "720bb71c-0b95-5a65-bd4a-4f4b0a32c25f",
                "code": "LIMA_KEDAI",
                "display_name": "Lima Kedai Toll Plaza",
                "highway_or_route": "PLUS / E2",
                "latitude": 1.596400,
                "longitude": 103.580500,
                "status": "operational",
                "base_toll": 2.80,
                "road_capacity": 1300,
                "simulation_profile": {
                    "baseline_demand": 0.48,
                    "peak_factor": 1.40,
                    "speed_profile": "intercity",
                },
            },
        ],
    )

    for table in ("traffic_records", "toll_prices", "detection_records", "toll_transactions"):
        op.add_column(table, sa.Column("location_id", UUID, nullable=True))
        op.execute(
            f"UPDATE {table} SET location_id = '{PENCHALA_LOCATION_ID}'::uuid WHERE location_id IS NULL"
        )
        op.alter_column(table, "location_id", nullable=False, server_default=PENCHALA_LOCATION_ID)
        op.create_foreign_key(
            f"fk_{table}_location_id",
            table,
            "toll_locations",
            ["location_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table}_location_id", table, ["location_id"])

    op.create_index(
        "ix_traffic_records_location_measured_at", "traffic_records", ["location_id", "measured_at"]
    )
    op.create_index(
        "ix_toll_prices_location_effective_at", "toll_prices", ["location_id", "effective_at"]
    )
    op.create_index(
        "ix_detection_records_location_detected_at",
        "detection_records",
        ["location_id", "detected_at"],
    )
    op.create_index(
        "ix_toll_transactions_location_processed_at",
        "toll_transactions",
        ["location_id", "processed_at"],
    )


def downgrade() -> None:
    for table, compound_index in (
        ("toll_transactions", "ix_toll_transactions_location_processed_at"),
        ("detection_records", "ix_detection_records_location_detected_at"),
        ("toll_prices", "ix_toll_prices_location_effective_at"),
        ("traffic_records", "ix_traffic_records_location_measured_at"),
    ):
        op.drop_index(compound_index, table_name=table)
        op.drop_index(f"ix_{table}_location_id", table_name=table)
        op.drop_constraint(f"fk_{table}_location_id", table, type_="foreignkey")
        op.drop_column(table, "location_id")
    op.drop_index("ix_toll_locations_code", table_name="toll_locations")
    op.drop_table("toll_locations")

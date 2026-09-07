"""Tune location-specific daily traffic profiles without changing the generator."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260907_0009"
down_revision = "20260907_0008"
branch_labels = None
depends_on = None


TUNED_PROFILES = {
    "PENCHALA": {
        "baseline_demand": 0.42,
        "peak_hours": [7, 8, 17, 18],
        "peak_factor": 1.60,
        "speed_profile": "urban",
        "speed_free_flow_kmh": 74,
        "speed_floor_kmh": 28,
        "variation": 0.020,
    },
    "DUKE": {
        "baseline_demand": 0.42,
        "peak_hours": [7, 8, 17, 18],
        "peak_factor": 1.75,
        "speed_profile": "urban",
        "speed_free_flow_kmh": 68,
        "speed_floor_kmh": 16,
        "variation": 0.012,
    },
    "NPE": {
        "baseline_demand": 0.38,
        "peak_hours": [8, 9, 17, 18],
        "peak_factor": 1.80,
        "speed_profile": "urban",
        "speed_free_flow_kmh": 78,
        "speed_floor_kmh": 20,
        "variation": 0.020,
    },
    "KESAS": {
        "baseline_demand": 0.41,
        "peak_hours": [6, 7, 16, 17, 18],
        "peak_factor": 1.78,
        "speed_profile": "urban",
        "speed_free_flow_kmh": 72,
        "speed_floor_kmh": 17,
        "variation": 0.020,
    },
}


def _locations_table() -> sa.Table:
    return sa.table(
        "toll_locations", sa.column("code"), sa.column("simulation_profile", postgresql.JSONB())
    )


def upgrade() -> None:
    locations = _locations_table()
    for code, profile in TUNED_PROFILES.items():
        op.execute(locations.update().where(locations.c.code == code).values(simulation_profile=profile))


def downgrade() -> None:
    locations = _locations_table()
    previous_profiles = {
        "PENCHALA": {"baseline_demand": 0.52, "peak_hours": [7, 8, 17, 18], "peak_factor": 1.45, "speed_profile": "urban", "speed_free_flow_kmh": 72, "speed_floor_kmh": 20, "variation": 0.06},
        "DUKE": {"baseline_demand": 0.68, "peak_hours": [7, 8, 9, 17, 18], "peak_factor": 1.10, "speed_profile": "urban", "speed_free_flow_kmh": 68, "speed_floor_kmh": 18, "variation": 0.08},
        "KESAS": {"baseline_demand": 0.42, "peak_hours": [6, 7, 16, 17], "peak_factor": 1.75, "speed_profile": "urban", "speed_free_flow_kmh": 76, "speed_floor_kmh": 22, "variation": 0.05},
        "NPE": {"baseline_demand": 0.36, "peak_hours": [8, 17, 18], "peak_factor": 2.05, "speed_profile": "urban", "speed_free_flow_kmh": 74, "speed_floor_kmh": 22, "variation": 0.04},
    }
    for code, profile in previous_profiles.items():
        op.execute(locations.update().where(locations.c.code == code).values(simulation_profile=profile))

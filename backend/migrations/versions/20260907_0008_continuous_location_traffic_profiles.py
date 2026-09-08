"""Tune seeded profiles for continuous, percentage-first traffic telemetry."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260907_0008"
down_revision = "20260906_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    locations = sa.table(
        "toll_locations", sa.column("code"), sa.column("simulation_profile", postgresql.JSONB())
    )
    # These remain configuration inputs.  The service derives congestion from
    # them and Malaysia time rather than treating baseline demand as a band.
    profiles = {
        "PENCHALA": {"baseline_demand": 0.52, "peak_hours": [7, 8, 17, 18], "peak_factor": 1.45, "speed_profile": "urban", "speed_free_flow_kmh": 72, "speed_floor_kmh": 20, "variation": 0.06},
        "DUKE": {"baseline_demand": 0.68, "peak_hours": [7, 8, 9, 17, 18], "peak_factor": 1.10, "speed_profile": "urban", "speed_free_flow_kmh": 68, "speed_floor_kmh": 18, "variation": 0.08},
        "KESAS": {"baseline_demand": 0.42, "peak_hours": [6, 7, 16, 17], "peak_factor": 1.75, "speed_profile": "urban", "speed_free_flow_kmh": 76, "speed_floor_kmh": 22, "variation": 0.05},
        "NPE": {"baseline_demand": 0.36, "peak_hours": [8, 17, 18], "peak_factor": 2.05, "speed_profile": "urban", "speed_free_flow_kmh": 74, "speed_floor_kmh": 22, "variation": 0.04},
    }
    for code, profile in profiles.items():
        op.execute(locations.update().where(locations.c.code == code).values(simulation_profile=profile))


def downgrade() -> None:
    locations = sa.table(
        "toll_locations", sa.column("code"), sa.column("simulation_profile", postgresql.JSONB())
    )
    profiles = {
        "PENCHALA": {"baseline_demand": 0.52, "peak_hours": [7, 8, 17, 18], "peak_factor": 1.45, "speed_profile": "urban", "speed_free_flow_kmh": 72, "speed_floor_kmh": 20, "variation": 0.06},
        "DUKE": {"baseline_demand": 0.68, "peak_hours": [7, 8, 9, 17, 18], "peak_factor": 1.65, "speed_profile": "urban", "speed_free_flow_kmh": 68, "speed_floor_kmh": 18, "variation": 0.08},
        "KESAS": {"baseline_demand": 0.40, "peak_hours": [6, 7, 16, 17], "peak_factor": 1.35, "speed_profile": "urban", "speed_free_flow_kmh": 76, "speed_floor_kmh": 22, "variation": 0.05},
        "NPE": {"baseline_demand": 0.32, "peak_hours": [8, 17, 18], "peak_factor": 1.25, "speed_profile": "urban", "speed_free_flow_kmh": 74, "speed_floor_kmh": 22, "variation": 0.04},
    }
    for code, profile in profiles.items():
        op.execute(locations.update().where(locations.c.code == code).values(simulation_profile=profile))

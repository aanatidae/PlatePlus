"""Align the simulated network with the Selangor Overview and add the webcam plaza.

The names and routes are geographic context only.  All traffic, pricing and
payment activity in PlatePlus remains synthetic.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260905_0005"
down_revision = "20260904_0004"
branch_labels = None
depends_on = None

SIMULATOR_LOCATION_ID = "c6da3070-d237-5e8a-b494-fd625318f92c"


def upgrade() -> None:
    locations = sa.table(
        "toll_locations",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code"), sa.column("display_name"), sa.column("highway_or_route"),
        sa.column("latitude"), sa.column("longitude"), sa.column("status"),
        sa.column("base_toll"), sa.column("road_capacity"),
        sa.column("simulation_profile", postgresql.JSONB()),
    )
    for code, values in {
        "SUNGAI_BESI": {"code": "DUKE", "display_name": "Simulated DUKE Toll Plaza", "highway_or_route": "DUKE / E33", "latitude": 3.176400, "longitude": 101.683000, "base_toll": 2.40, "road_capacity": 1200, "simulation_profile": {"baseline_demand": 0.55, "peak_factor": 1.60, "speed_profile": "urban"}},
        "AYER_KEROH": {"code": "KESAS", "display_name": "Simulated KESAS Toll Plaza", "highway_or_route": "KESAS / E5", "latitude": 3.057500, "longitude": 101.568500, "base_toll": 3.20, "road_capacity": 1500, "simulation_profile": {"baseline_demand": 0.36, "peak_factor": 1.30, "speed_profile": "urban"}},
        "LIMA_KEDAI": {"code": "NPE", "display_name": "Simulated NPE Toll Plaza", "highway_or_route": "NPE / E10", "latitude": 3.095000, "longitude": 101.672000, "base_toll": 2.80, "road_capacity": 1300, "simulation_profile": {"baseline_demand": 0.48, "peak_factor": 1.40, "speed_profile": "urban"}},
    }.items():
        op.execute(
            locations.update().where(locations.c.code == code).values(**values)
        )
    op.bulk_insert(locations, [{
        "id": SIMULATOR_LOCATION_ID, "code": "SIMULATOR", "display_name": "Simulator Toll Plaza",
        "highway_or_route": "LDP / E11 · Webcam ALPR", "latitude": 3.108000,
        "longitude": 101.612000, "status": "operational", "base_toll": 2.00,
        "road_capacity": 10,
        "simulation_profile": {"telemetry_source": "webcam_alpr", "capacity_window_hours": 1},
    }])


def downgrade() -> None:
    op.execute("DELETE FROM toll_locations WHERE code = 'SIMULATOR'")
    locations = sa.table("toll_locations", sa.column("code"), sa.column("display_name"), sa.column("highway_or_route"), sa.column("latitude"), sa.column("longitude"), sa.column("base_toll"), sa.column("road_capacity"))
    for code, values in {
        "DUKE": {"code": "SUNGAI_BESI", "display_name": "Sungai Besi Toll Plaza", "highway_or_route": "BESRAYA / E9", "latitude": 3.072800, "longitude": 101.710500, "base_toll": 2.40, "road_capacity": 1200},
        "KESAS": {"code": "AYER_KEROH", "display_name": "Ayer Keroh Toll Plaza", "highway_or_route": "PLUS / E2", "latitude": 2.271100, "longitude": 102.282400, "base_toll": 3.20, "road_capacity": 1500},
        "NPE": {"code": "LIMA_KEDAI", "display_name": "Lima Kedai Toll Plaza", "highway_or_route": "PLUS / E2", "latitude": 1.596400, "longitude": 103.580500, "base_toll": 2.80, "road_capacity": 1300},
    }.items():
        op.execute(locations.update().where(locations.c.code == code).values(**values))

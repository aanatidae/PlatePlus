"""Align the normal network without transferring unrelated historical records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261007_0014"
down_revision = "20261002_0013"
branch_labels = None
depends_on = None

NEW_LOCATIONS = (
    {"id": "f6716a12-3f23-5b31-88ca-277f9b184101", "code": "AKLEH",
     "display_name": "Simulated AKLEH Toll Plaza", "highway_or_route": "AKLEH",
     "latitude": 3.160000, "longitude": 101.735000, "base_toll": 2.40,
     "road_capacity": 1200, "simulation_profile": {
         "baseline_demand": .42, "peak_hours": [7, 8, 17, 18], "peak_factor": 1.75,
         "speed_profile": "urban", "speed_free_flow_kmh": 68, "speed_floor_kmh": 16,
         "variation": .012}},
    {"id": "b8982e24-420c-549d-a395-a0a75c0d4102", "code": "GRAND_SAGA",
     "display_name": "Simulated Grand Saga Toll Plaza", "highway_or_route": "Grand Saga",
     "latitude": 3.045000, "longitude": 101.765000, "base_toll": 3.20,
     "road_capacity": 1500, "simulation_profile": {
         "baseline_demand": .41, "peak_hours": [6, 7, 16, 17, 18], "peak_factor": 1.78,
         "speed_profile": "urban", "speed_free_flow_kmh": 72, "speed_floor_kmh": 17,
         "variation": .020}},
)


def _locations():
    return sa.table("toll_locations", sa.column("id", postgresql.UUID()),
                    *(sa.column(name) for name in ("code", "display_name", "highway_or_route",
                      "latitude", "longitude", "base_toll", "road_capacity", "status")),
                    sa.column("simulation_profile", postgresql.JSONB()))


def upgrade():
    locations = _locations()
    # Penchala already belongs to LDP: retain its ID, configuration and history.
    op.execute(locations.update().where(locations.c.code == "PENCHALA").values(
        code="LDP", display_name="Simulated LDP Toll Plaza"))
    # DUKE/KESAS history must never appear to have occurred at a different highway.
    op.execute(locations.update().where(locations.c.code.in_(("DUKE", "KESAS"))).values(
        status="retired"))
    op.bulk_insert(locations, [dict(item, status="operational") for item in NEW_LOCATIONS])


def downgrade():
    # RESTRICT foreign keys intentionally refuse removal if V3 locations have
    # acquired history. Never delete or reassign that history to permit rollback.
    locations = _locations()
    op.execute(locations.delete().where(locations.c.code.in_(("AKLEH", "GRAND_SAGA"))))
    op.execute(locations.update().where(locations.c.code.in_(("DUKE", "KESAS"))).values(
        status="operational"))
    op.execute(locations.update().where(locations.c.code == "LDP").values(
        code="PENCHALA", display_name="Penchala Toll Plaza"))

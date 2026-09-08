"""Location-aware API contracts for the simulated toll network."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TollLocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    display_name: str
    highway_or_route: str
    latitude: Decimal
    longitude: Decimal
    status: str
    base_toll: Decimal
    road_capacity: int
    simulation_profile: dict
    created_at: datetime
    updated_at: datetime

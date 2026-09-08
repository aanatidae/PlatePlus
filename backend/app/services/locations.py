"""Shared defaults for the single-location compatibility boundary."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TollLocation

DEFAULT_TOLL_LOCATION_CODE = "PENCHALA"


def default_toll_location_id(database: Session) -> UUID:
    """Return the legacy single-location context used until selection is introduced."""
    location_id = database.scalar(
        select(TollLocation.id).where(TollLocation.code == DEFAULT_TOLL_LOCATION_CODE)
    )
    if location_id is None:
        raise ValueError("The default Penchala toll location is not initialized. Run migrations.")
    return location_id

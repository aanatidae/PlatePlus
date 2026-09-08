from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import DetectionRecord, DynamicPricingRule, TollLocation
from app.services.traffic.webcam_crossings import (
    prepare_webcam_crossing_price,
    webcam_crossing_state,
)


@compiles(JSONB, "sqlite")
def sqlite_json(type_, compiler, **kw):
    return "JSON"


@pytest.fixture
def webcam_network():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as database:
        location = TollLocation(code="SIMULATOR", display_name="Simulator Toll Plaza", highway_or_route="LDP / E11 · Webcam ALPR", latitude=3.1, longitude=101.6, base_toll=Decimal("2.00"), road_capacity=10)
        database.add(location)
        database.add_all([
            DynamicPricingRule(scenario="normal", congestion_category="low", minimum_percentage=0, maximum_percentage=30, amount=2),
            DynamicPricingRule(scenario="moderate", congestion_category="moderate", minimum_percentage=Decimal("30.01"), maximum_percentage=60, amount=3),
            DynamicPricingRule(scenario="peak_hour", congestion_category="high", minimum_percentage=Decimal("60.01"), maximum_percentage=80, amount=4),
            DynamicPricingRule(scenario="severe", congestion_category="severe", minimum_percentage=Decimal("80.01"), maximum_percentage=100, amount=5),
        ])
        database.commit()
        yield database, location
    engine.dispose()


def _crossing(database, location, when, status="accepted"):
    database.add(DetectionRecord(location_id=location.id, detected_at=when, normalized_plate="VAA1234", detection_confidence=.9, status=status, source="webcam"))


def test_webcam_crossings_drive_rolling_congestion_and_pricing(webcam_network):
    database, location = webcam_network
    now = datetime.now(UTC)
    for _ in range(5):
        _crossing(database, location, now)
    _crossing(database, location, now - timedelta(hours=1, seconds=1))
    _crossing(database, location, now, status="low_confidence")
    database.commit()

    telemetry = webcam_crossing_state(database, location, now)["telemetry"]

    assert telemetry["vehicles_per_hour"] == 5
    assert telemetry["congestion_percentage"] == Decimal("50.00")
    assert telemetry["congestion_category"] == "moderate"
    assert telemetry["current_toll_price"] == Decimal("3.00")
    assert telemetry["average_speed_kmh"] is None


def test_webcam_crossings_cap_at_one_hundred_and_prepare_the_next_price(webcam_network):
    database, location = webcam_network
    now = datetime.now(UTC)
    for _ in range(10):
        _crossing(database, location, now)
    database.commit()

    assert webcam_crossing_state(database, location, now)["telemetry"]["congestion_percentage"] == Decimal("100.00")
    prepare_webcam_crossing_price(database, location, now)
    database.commit()
    assert webcam_crossing_state(database, location, now)["telemetry"]["vehicles_per_hour"] == 10

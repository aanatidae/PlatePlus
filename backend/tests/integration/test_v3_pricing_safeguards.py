"""Exercise the actual V3 location bases with stored pricing safeguards."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import TollLocation, TollPrice, TrafficSimulationSettings
from app.services.traffic.pricing import decide_price
from app.services.traffic.webcam_crossings import webcam_crossing_state


@pytest.mark.parametrize("code", ["LDP", "AKLEH", "NPE", "GRAND_SAGA"])
def test_v3_base_toll_obeys_floor_cap_interval_and_hysteresis(database, code):
    location = database.scalar(select(TollLocation).where(TollLocation.code == code))
    settings = database.scalar(select(TrafficSimulationSettings))
    now = datetime.now(UTC)
    settings.minimum_toll = location.base_toll + Decimal("0.10")
    settings.maximum_toll_multiplier = Decimal(2)
    settings.minimum_price_change_minutes = 5
    settings.pricing_hysteresis_percentage = Decimal(2)
    database.flush()
    assert decide_price(database, settings, location, Decimal(10), now).amount == settings.minimum_toll
    assert decide_price(database, settings, location, Decimal(90), now).amount == location.base_toll * 2
    previous = TollPrice(location_id=location.id, effective_at=now - timedelta(minutes=1),
                         amount=location.base_toll * Decimal("1.5"), congestion_category="moderate")
    database.add(previous)
    database.flush()
    held = decide_price(database, settings, location, Decimal(75), now)
    assert held.reason == "minimum change interval hold" and held.amount == previous.amount
    previous.effective_at = now - timedelta(minutes=10)
    database.flush()
    held = decide_price(database, settings, location, Decimal("60.01"), now)
    assert held.reason == "hysteresis hold near band boundary" and held.amount == previous.amount
    changed = decide_price(database, settings, location, Decimal(70), now)
    assert changed.amount == location.base_toll * 2 and changed.reason == "current congestion band"


def test_simulator_explains_the_held_band_with_its_applied_multiplier(database):
    from app.models import DetectionRecord

    now = datetime.now(UTC)
    location = database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))
    settings = database.scalar(select(TrafficSimulationSettings))
    settings.minimum_price_change_minutes = 5
    database.add(TollPrice(location_id=location.id, effective_at=now - timedelta(minutes=1),
                           amount=location.base_toll * Decimal("1.5"), congestion_category="moderate"))
    for _ in range(7):
        database.add(DetectionRecord(location_id=location.id, detected_at=now,
                                    detection_confidence=.99, status="accepted", source="webcam_alpr"))
    database.flush()
    telemetry = webcam_crossing_state(database, location, now)["telemetry"]
    assert telemetry["congestion_percentage"] == Decimal(70)
    assert telemetry["congestion_category"] == "moderate"
    assert telemetry["congestion_multiplier"] == Decimal("1.5")
    assert telemetry["current_toll_price"] == location.base_toll * Decimal("1.5")


def test_foreign_charge_edit_does_not_reprice_or_change_congestion_policy(database, database_app, admin_auth_headers):
    from fastapi.testclient import TestClient

    from app.models import AdminAuditLog, DynamicPricingRule
    from app.services.traffic.pricing import reprice_current_locations

    reprice_current_locations(database, database.scalar(select(TrafficSimulationSettings)))
    database.commit()
    before_prices = [(row.id, row.amount, row.congestion_category) for row in database.scalars(select(TollPrice).order_by(TollPrice.id))]
    before_rules = [(row.id, row.multiplier, row.minimum_percentage, row.maximum_percentage) for row in database.scalars(select(DynamicPricingRule).order_by(DynamicPricingRule.id))]
    response = TestClient(database_app).put("/api/data/foreign-vehicle-charge", headers=admin_auth_headers, json={"amount": "12.50"})
    assert response.status_code == 200 and Decimal(response.json()["amount"]) == Decimal("12.50")
    assert [(row.id, row.amount, row.congestion_category) for row in database.scalars(select(TollPrice).order_by(TollPrice.id))] == before_prices
    assert [(row.id, row.multiplier, row.minimum_percentage, row.maximum_percentage) for row in database.scalars(select(DynamicPricingRule).order_by(DynamicPricingRule.id))] == before_rules
    assert database.scalar(select(AdminAuditLog).where(AdminAuditLog.action == "foreign_vehicle_charge_updated"))

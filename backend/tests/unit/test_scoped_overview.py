"""Query/HTTP behavior on temporary SQLite; PostgreSQL migrations remain integration-only."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import require_admin
from app.api.database import router as data_router
from app.api.intelligence import router as intelligence_router
from app.api.live import router as live_router
from app.api.locations import router as location_router
from app.db.base import Base
from app.db.session import get_db
from app.models import (
    DetectionRecord,
    DynamicPricingRule,
    TollLocation,
    TollPrice,
    TollTransaction,
    TrafficRecord,
    TrafficSimulationSettings,
)


@compiles(JSONB, "sqlite")
def sqlite_json(type_, compiler, **kw):
    return "JSON"


@pytest.fixture
def network():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(TrafficSimulationSettings(singleton_key="default"))
        locations = [
            TollLocation(
                code=f"TEST_{i}",
                display_name=f"Test toll {i}",
                highway_or_route="Test route",
                latitude=3,
                longitude=101,
                base_toll=2 + i,
                road_capacity=1000 * (i + 1),
            )
            for i in range(2)
        ]
        db.add_all(locations)
        db.flush()
        now = datetime.now(UTC)
        for index, (name, category, low, high) in enumerate([
            ("normal", "low", "0", "30"),
            ("moderate", "moderate", "30.01", "60"),
            ("peak_hour", "high", "60.01", "80"),
            ("severe", "severe", "80.01", "100"),
        ]):
            db.add(
                DynamicPricingRule(
                    scenario=name,
                    congestion_category=category,
                    minimum_percentage=Decimal(low),
                    maximum_percentage=Decimal(high),
                    amount=2 + index,
                )
            )
        for index, location in enumerate(locations):
            congestion = 20 if index == 0 else 90
            db.add(
                TrafficRecord(
                    location_id=location.id,
                    measured_at=now,
                    vehicle_count=200 if index == 0 else 1800,
                    road_capacity=location.road_capacity,
                    congestion_percentage=congestion,
                    congestion_category="low" if index == 0 else "severe",
                )
            )
            db.add(
                TollPrice(
                    location_id=location.id,
                    effective_at=now,
                    amount=2 + index,
                    congestion_category="low",
                )
            )
            db.add(
                DetectionRecord(
                    location_id=location.id,
                    detected_at=now,
                    normalized_plate=f"TEST{index}",
                    detection_confidence=0.9,
                    ocr_confidence=0 if index == 0 else 0.8,
                    status="accepted",
                )
            )
            db.add(
                TollTransaction(
                    location_id=location.id,
                    processed_at=now,
                    amount=2 + index,
                    status="successful" if index == 0 else "failed",
                    idempotency_key=f"test-toll-{index}",
                )
            )
        db.add(
            DetectionRecord(
                location_id=locations[0].id,
                detected_at=now - timedelta(hours=2),
                normalized_plate="OLD1",
                detection_confidence=0.9,
                status="accepted",
            )
        )
        db.commit()
        app = FastAPI()
        for router in [live_router, location_router, data_router, intelligence_router]:
            app.include_router(router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = lambda: None
        yield TestClient(app), db, locations
    engine.dispose()


def test_network_aggregation_uses_capacity_and_all_payment_outcomes(network):
    client, _, _ = network
    response = client.get("/api/live/overview?scope=all_locations")
    assert response.status_code == 200, response.text
    data = response.json()
    assert float(data["live"]["traffic"]["congestion_percentage"]) == pytest.approx(200 / 3)
    assert data["live"]["traffic"]["vehicles_per_hour"] == 2000
    assert float(data["live"]["price"]["amount"]) == 2.5
    assert data["metrics"]["detections"] == 2
    assert data["metrics"]["transactions"] == 2
    assert data["metrics"]["successful_transactions"] == 1
    assert float(data["metrics"]["revenue"]) == 2
    assert float(data["metrics"]["average_recognition_confidence"]) == 0.4
    assert data["metrics"]["severe_locations"] == 1


def test_selected_overview_returns_only_its_recent_records_and_never_writes(network):
    client, db, locations = network
    writes = []

    def observe(connection, cursor, statement, *args):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    event.listen(db.bind, "before_cursor_execute", observe)
    data = client.get(f"/api/live/overview?location_id={locations[0].id}").json()
    assert data["metrics"]["detections"] == 1
    assert {item["location_id"] for item in data["detections"]["items"]} == {str(locations[0].id)}
    assert {item["location_id"] for item in data["transactions"]["items"]} == {str(locations[0].id)}
    assert len(data["locations"]) == 1
    assert writes == []


@pytest.mark.parametrize("persisted_traffic", [True, False])
def test_live_congestion_uses_current_rules_without_overwriting_recorded_price(
    network, monkeypatch, persisted_traffic
):
    from app.services.traffic import simulation

    client, db, locations = network
    location = locations[0]
    traffic = db.scalar(select(TrafficRecord).where(TrafficRecord.location_id == location.id))
    # Reproduce NPE: current 33% traffic alongside an older Peak Hour toll.
    traffic.congestion_percentage = Decimal("33.00")
    traffic.congestion_category = "high"  # Historical category must not override current policy.
    price = db.scalar(select(TollPrice).where(TollPrice.location_id == location.id))
    price.congestion_category = "high"
    price.amount = Decimal("5.60")
    if not persisted_traffic:
        db.delete(traffic)
        monkeypatch.setattr(simulation, "profile_congestion_for_time", lambda *_: Decimal("33.00"))
    db.commit()

    writes = []

    def observe(connection, cursor, statement, *args):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    event.listen(db.bind, "before_cursor_execute", observe)
    try:
        paths = [
            (f"/api/locations/{location.id}/live", lambda data: data["telemetry"]),
            ("/api/locations/network/live", lambda data: next(
                item["telemetry"] for item in data["locations"] if item["id"] == str(location.id)
            )),
            (f"/api/live/overview?location_id={location.id}", lambda data: data["live"]["traffic"]),
            ("/api/live/overview?scope=all_locations", lambda data: next(
                item["telemetry"] for item in data["locations"] if item["location"]["id"] == str(location.id)
            )),
        ]
        for path, telemetry in paths:
            response = client.get(path)
            assert response.status_code == 200, response.text
            live = telemetry(response.json())
            assert Decimal(str(live["congestion_percentage"])) == Decimal(33)
            assert live["congestion_category"] == "moderate"
            assert live["pricing_category"] == "high"
            assert Decimal(str(live["current_toll_price"])) == Decimal("5.60")
        assert writes == []
    finally:
        event.remove(db.bind, "before_cursor_execute", observe)

    # Configurable ranges, rather than fixed UI thresholds, determine the label.
    rules = {rule.scenario: rule for rule in db.scalars(select(DynamicPricingRule))}
    rules["normal"].maximum_percentage = Decimal(40)
    rules["moderate"].minimum_percentage = Decimal("40.01")
    db.commit()
    live = client.get(f"/api/locations/{location.id}/live").json()["telemetry"]
    assert live["congestion_category"] == "low"
    assert live["pricing_category"] == "high"
    db.refresh(price)
    assert price.amount == Decimal("5.60") and price.congestion_category == "high"


def test_intelligence_summary_exposes_thresholds_and_location_trace(network):
    client, _, locations = network
    response = client.get(f"/api/intelligence/summary?location_id={locations[0].id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["thresholds"] == {"detection": 0.5, "ocr": 0.7}
    assert data["evaluation"]["ocr"]["exact_match_accuracy_percent"] == 84.1
    assert data["evaluation"]["development"]["exact_matches"] == 125
    assert data["evaluation"]["development"]["positive_detector_false_negatives"] == 0
    assert data["evaluation"]["development"]["positive_detector_images"] == 146
    assert data["evaluation"]["origin"]["fixture_type"] == "synthetic_text_only"
    assert data["evaluation"]["origin"]["exact_matches"] == 25
    assert "Not field accuracy" in data["evaluation"]["origin"]["note"]
    assert data["alpr_trace"]["stages"][0]["name"] == "Detector result"
    assert data["pricing_trace"]["location_name"] == "Test toll 0"
    assert data["pricing_trace"]["policy"]["rule_version"] == 1


def test_history_filters_apply_before_limit_and_are_location_scoped(network):
    client, _, locations = network
    response = client.get(f"/api/data/detections?location_id={locations[0].id}&plate=OLD&limit=1")
    assert [item["normalized_plate"] for item in response.json()] == ["OLD1"]
    assert client.get(f"/api/data/detections?location_id={locations[1].id}&plate=OLD").json() == []
    assert (
        client.get("/api/data/transactions?transaction_status=failed&minimum_amount=3").json()[0][
            "status"
        ]
        == "failed"
    )
    assert client.get("/api/data/toll-prices?start_at=2030-01-01T00:00:00%2B08:00").json() == []
    assert (
        client.get(
            "/api/data/detections?start_at=2030-01-01T00:00:00Z&end_at=2020-01-01T00:00:00Z"
        ).status_code
        == 422
    )


def test_unknown_locations_and_missing_telemetry_are_explicit(network):
    client, db, _ = network
    assert client.get(f"/api/live/overview?location_id={uuid4()}").status_code == 404
    for rule in db.scalars(select(DynamicPricingRule)):
        db.delete(rule)
    db.commit()
    data = client.get("/api/live/overview?scope=all_locations").json()
    assert data["live"]["traffic"] is None
    assert data["metrics"]["locations_reporting"] == 0
    assert data["metrics"]["transactions"] == 2


def test_empty_network_has_no_invented_telemetry(network):
    client, db, _ = network
    for model in [TollTransaction, DetectionRecord, TollPrice, TrafficRecord, TollLocation]:
        for row in db.scalars(select(model)):
            db.delete(row)
        db.flush()
    db.commit()
    data = client.get("/api/live/overview?scope=all_locations").json()
    assert data["locations"] == []
    assert data["live"] == {"traffic": None, "price": None}
    assert data["metrics"]["transactions"] == 0

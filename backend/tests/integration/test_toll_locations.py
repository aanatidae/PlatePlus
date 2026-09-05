"""PostgreSQL coverage for the multi-toll-location foundation."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import DetectionRecord, TollLocation, TollPrice, TollTransaction, TrafficRecord


def test_live_overview_scopes_activity_and_network_totals(database, database_app, admin_auth_headers):
    locations = list(database.scalars(select(TollLocation).order_by(TollLocation.code)))
    now = datetime.now(UTC)
    for index, location in enumerate(locations):
        database.add(DetectionRecord(location_id=location.id, detected_at=now,
                                    normalized_plate=f"TEST{index}", detection_confidence=.9, status="accepted"))
        database.add(TollTransaction(location_id=location.id, processed_at=now, amount=2,
                                    status="successful" if index == 0 else "failed", idempotency_key=f"network-test-{index}"))
    database.commit()
    client = TestClient(database_app)
    network = client.get("/api/live/overview?scope=all_locations", headers=admin_auth_headers)
    assert network.status_code == 200, network.text
    assert network.json()["metrics"]["transactions"] == 4
    assert network.json()["metrics"]["successful_transactions"] == 1
    assert Decimal(network.json()["metrics"]["revenue"]) == Decimal("2")
    location = client.get(f"/api/live/overview?location_id={locations[1].id}", headers=admin_auth_headers)
    assert location.status_code == 200, location.text
    assert location.json()["metrics"]["detections"] == 1
    assert {item["location_id"] for item in location.json()["detections"]["items"]} == {str(locations[1].id)}
    assert {item["location_id"] for item in location.json()["transactions"]["items"]} == {str(locations[1].id)}
    assert client.get("/api/live/overview?scope=all_locations").status_code == 401


def test_location_history_filters_use_malaysia_date_boundaries(database, database_app, admin_auth_headers):
    location = database.scalar(select(TollLocation))
    database.add_all([
        DetectionRecord(location_id=location.id, detected_at=datetime(2026, 9, 4, 16, 1, tzinfo=UTC),
                        normalized_plate="MATCH1", detection_confidence=.9, status="accepted"),
        DetectionRecord(location_id=location.id, detected_at=datetime(2026, 9, 4, 15, 59, tzinfo=UTC),
                        normalized_plate="MATCH2", detection_confidence=.9, status="accepted"),
    ])
    database.commit()
    response = TestClient(database_app).get("/api/data/detections", headers=admin_auth_headers,
        params={"location_id": str(location.id), "start_at": "2026-09-05T00:00:00+08:00",
                "end_at": "2026-09-05T23:59:59+08:00", "plate": "MATCH", "limit": 1})
    assert response.status_code == 200, response.text
    assert [item["normalized_plate"] for item in response.json()] == ["MATCH1"]


def test_migration_seeds_the_simulated_toll_network(database) -> None:
    locations = list(database.scalars(select(TollLocation).order_by(TollLocation.code)))

    assert [location.code for location in locations] == [
        "AYER_KEROH",
        "LIMA_KEDAI",
        "PENCHALA",
        "SUNGAI_BESI",
    ]
    assert all(location.status == "operational" for location in locations)
    assert all(location.road_capacity > 0 for location in locations)
    assert all(location.base_toll >= Decimal("0.00") for location in locations)


def test_operational_records_default_to_penchala_and_keep_location_ownership(database) -> None:
    now = datetime.now(UTC)
    traffic = TrafficRecord(
        measured_at=now,
        vehicle_count=100,
        road_capacity=1_000,
        congestion_percentage=Decimal("10.00"),
        congestion_category="low",
    )
    database.add(traffic)
    database.flush()
    price = TollPrice(
        traffic_record_id=traffic.id,
        effective_at=now,
        amount=Decimal("2.00"),
        congestion_category="low",
    )
    detection = DetectionRecord(
        detected_at=now,
        detection_confidence=Decimal("0.9000"),
        status="accepted",
    )
    database.add_all([price, detection])
    database.flush()
    transaction = TollTransaction(
        toll_price_id=price.id,
        detection_id=detection.id,
        idempotency_key="location-default-0001",
        processed_at=now,
        amount=Decimal("2.00"),
        status="successful",
    )
    database.add(transaction)
    database.flush()

    penchala = database.scalar(select(TollLocation).where(TollLocation.code == "PENCHALA"))
    assert penchala is not None
    assert {
        traffic.location_id,
        price.location_id,
        detection.location_id,
        transaction.location_id,
    } == {penchala.id}


def test_location_endpoints_filter_records_and_reject_unknown_ids(
    database, database_app, admin_auth_headers
) -> None:
    penchala, other = list(database.scalars(select(TollLocation).order_by(TollLocation.code)))[2:4]
    now = datetime.now(UTC)
    database.add_all(
        [
            DetectionRecord(
                location_id=penchala.id,
                detected_at=now,
                detection_confidence=Decimal("0.9"),
                status="accepted",
            ),
            DetectionRecord(
                location_id=other.id,
                detected_at=now,
                detection_confidence=Decimal("0.9"),
                status="accepted",
            ),
        ]
    )
    database.commit()
    client = TestClient(database_app)
    listed = client.get("/api/locations", headers=admin_auth_headers)
    filtered = client.get(
        f"/api/data/detections?location_id={penchala.id}", headers=admin_auth_headers
    )
    missing = client.get(
        "/api/locations/00000000-0000-0000-0000-000000000000", headers=admin_auth_headers
    )
    assert listed.status_code == 200 and len(listed.json()) == 4
    assert filtered.status_code == 200 and {item["location_id"] for item in filtered.json()} == {
        str(penchala.id)
    }
    assert missing.status_code == 404

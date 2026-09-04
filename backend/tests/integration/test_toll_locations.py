"""PostgreSQL coverage for the multi-toll-location foundation."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import DetectionRecord, TollLocation, TollPrice, TollTransaction, TrafficRecord


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

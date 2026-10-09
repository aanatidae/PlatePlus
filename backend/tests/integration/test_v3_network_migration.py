"""V3 network migration preserves unrelated history and isolates retired roads."""

from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import DetectionRecord, TollLocation, TollTransaction, TrafficSimulationSettings
from app.services.traffic.simulation import run_network_simulation


def test_network_upgrade_preserves_old_history_and_round_trips(test_engine, reset_schema):
    config = Config("alembic.ini")
    try:
        reset_schema("20261002_0013")
        with test_engine.begin() as connection:
            original = connection.execute(text(
                "SELECT id, code, display_name, base_toll, road_capacity, simulation_profile::text "
                "FROM toll_locations ORDER BY code"
            )).all()
            for location in original:
                connection.execute(text(
                    "INSERT INTO detection_records (location_id, normalized_plate, detected_at, "
                    "detection_confidence, status, source) VALUES (:id, :code, now(), .99, 'accepted', 'test')"
                ), {"id": location.id, "code": location.code})
            history = connection.execute(text(
                "SELECT id, location_id, normalized_plate, detected_at FROM detection_records ORDER BY id"
            )).all()
        command.upgrade(config, "head")
        with test_engine.connect() as connection:
            assert connection.execute(text(
                "SELECT id, location_id, normalized_plate, detected_at FROM detection_records ORDER BY id"
            )).all() == history
            current = dict(connection.execute(text("SELECT code, id FROM toll_locations")).all())
            old = {row.code: row.id for row in original}
            assert current["LDP"] == old["PENCHALA"]
            assert current["NPE"] == old["NPE"] and current["SIMULATOR"] == old["SIMULATOR"]
            assert current["AKLEH"] != old["DUKE"] and current["GRAND_SAGA"] != old["KESAS"]
            assert set(connection.scalars(text(
                "SELECT code FROM toll_locations WHERE status='retired'"
            ))) == {"DUKE", "KESAS"}
        command.downgrade(config, "20261002_0013")
        with test_engine.connect() as connection:
            assert connection.execute(text(
                "SELECT id, code, display_name, base_toll, road_capacity, simulation_profile::text "
                "FROM toll_locations ORDER BY code"
            )).all() == original
        command.upgrade(config, "head")
        # A populated new highway cannot be rolled back by deleting its history.
        with test_engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO detection_records (location_id, detected_at, detection_confidence, status) "
                "SELECT id, now(), .99, 'accepted' FROM toll_locations WHERE code='AKLEH'"
            ))
        with pytest.raises(IntegrityError):
            command.downgrade(config, "20261002_0013")
        with test_engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261009_0015"
            assert connection.scalar(text("SELECT count(*) FROM detection_records")) == len(history) + 1
    finally:
        reset_schema()


def test_retired_history_is_queryable_but_excluded_from_live_network(
    database, database_app, admin_auth_headers
):
    retired = database.scalar(select(TollLocation).where(TollLocation.status == "retired"))
    database.add(DetectionRecord(location_id=retired.id, detected_at=datetime.now(UTC),
                                 detection_confidence=.99, status="accepted"))
    database.add(TollTransaction(location_id=retired.id, processed_at=datetime.now(UTC),
                                amount=99, status="successful", idempotency_key="retired-network-history"))
    database.commit()
    client = TestClient(database_app)
    listed = client.get("/api/locations", headers=admin_auth_headers).json()
    assert {item["code"] for item in listed} == {"LDP", "AKLEH", "NPE", "GRAND_SAGA", "SIMULATOR"}
    for path in ("/api/locations/network/live", "/api/live/overview?scope=all_locations"):
        response = client.get(path, headers=admin_auth_headers)
        assert response.status_code == 200, response.text
        assert response.json()["metrics"]["detections"] == 0
        assert response.json()["metrics"]["transactions"] == 0
    history = client.get("/api/data/detections", params={"location_id": str(retired.id)},
                         headers=admin_auth_headers)
    assert history.status_code == 200 and len(history.json()) == 1
    assert client.get(f"/api/locations/{retired.id}", headers=admin_auth_headers).json()["status"] == "retired"
    settings = database.scalar(select(TrafficSimulationSettings))
    results = run_network_simulation(database, settings, source="scheduled", seed=14)
    assert {result.traffic_record.location.code for result in results} == {"LDP", "AKLEH", "NPE", "GRAND_SAGA"}

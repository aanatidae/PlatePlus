"""Verify fresh/legacy V3 convergence only on the dedicated test database."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.db import seed
from app.models import DetectionRecord, TollLocation, TollPrice, TollTransaction, TrafficRecord


def _schema(engine):
    inspector = inspect(engine)
    return {
        table: {
            "columns": [(c["name"], str(c["type"]), c["nullable"], c["default"])
                        for c in inspector.get_columns(table)],
            "checks": sorted((c["name"], c["sqltext"])
                             for c in inspector.get_check_constraints(table)),
            "foreign_keys": sorted((tuple(c["constrained_columns"]), c["referred_table"],
                                    tuple(c["referred_columns"]))
                                   for c in inspector.get_foreign_keys(table)),
            "indexes": sorted((c["name"], tuple(c["column_names"]), c["unique"])
                              for c in inspector.get_indexes(table)),
        } for table in inspector.get_table_names()
    }


def _seed_state(engine):
    with engine.connect() as connection:
        return {
            "fleet": connection.execute(text(
                "SELECT v.plate_number, v.registration_origin, u.email, a.balance, "
                "a.opening_balance, a.is_primary FROM vehicles v JOIN users u ON u.id=v.user_id "
                "JOIN accounts a ON a.user_id=u.id ORDER BY v.plate_number"
            )).all(),
            "locations": connection.execute(text(
                "SELECT id, code, base_toll, road_capacity, simulation_profile::text "
                "FROM toll_locations ORDER BY code"
            )).all(),
            "charge": connection.execute(text(
                "SELECT singleton_key, amount FROM foreign_vehicle_charge_settings"
            )).all(),
            "ledger_count": connection.scalar(text("SELECT count(*) FROM wallet_ledger_entries")),
            "head": connection.scalar(text("SELECT version_num FROM alembic_version")),
        }


@pytest.mark.parametrize("source", ["uploaded_image", "webcam_alpr"])
def test_fresh_and_upgraded_v3_converge_and_preserve_simulator_history(test_engine, reset_schema, monkeypatch, source):
    config = Config("alembic.ini")
    sessions = sessionmaker(bind=test_engine, expire_on_commit=False)
    monkeypatch.setattr(seed, "SessionLocal", sessions)
    try:
        reset_schema()
        seed.seed_demo_data()
        fresh_schema, fresh_seed = _schema(test_engine), _seed_state(test_engine)
        seed.seed_demo_data()
        assert _seed_state(test_engine) == fresh_seed
        assert fresh_seed["head"] == "20261009_0015"
        assert len(fresh_seed["fleet"]) == fresh_seed["ledger_count"] == 99

        # Start a genuine pre-V3 database with historical crossings, not a
        # downgrade of SG data that would lose its origin/charge information.
        reset_schema("20260908_0011")
        now = datetime.now(UTC)
        with test_engine.begin() as connection:
            user_id = connection.scalar(text(
                "INSERT INTO users (full_name, email) VALUES ('Aina Rahman', 'aina.rahman@example.test') RETURNING id"
            ))
            vehicle_id = connection.scalar(text(
                "INSERT INTO vehicles (user_id, plate_number) VALUES (:user, 'VAA1234') RETURNING id"
            ), {"user": user_id})
            simulator_id = connection.scalar(text("SELECT id FROM toll_locations WHERE code='SIMULATOR'"))
            traffic_id = connection.scalar(text(
                "INSERT INTO traffic_records (location_id, measured_at, vehicle_count, road_capacity, "
                "congestion_percentage, congestion_category) VALUES (:location, :now, 1, 10, 10, 'low') RETURNING id"
            ), {"location": simulator_id, "now": now})
            price_id = connection.scalar(text(
                "INSERT INTO toll_prices (location_id, traffic_record_id, effective_at, amount, congestion_category) "
                "VALUES (:location, :traffic, :now, 2.40, 'low') RETURNING id"
            ), {"location": simulator_id, "traffic": traffic_id, "now": now})
            detection_id = connection.scalar(text(
                "INSERT INTO detection_records (location_id, vehicle_id, detected_at, detection_confidence, status, source, normalized_plate) "
                "VALUES (:location, :vehicle, :now, .99, 'accepted', :source, 'VAA1234') RETURNING id"
            ), {"location": simulator_id, "vehicle": vehicle_id, "now": now, "source": source})
            transaction_id = connection.scalar(text(
                "INSERT INTO toll_transactions (location_id, vehicle_id, toll_price_id, detection_id, idempotency_key, "
                "processed_at, amount, status) VALUES (:location, :vehicle, :price, :detection, 'legacy-v3-migration', "
                ":now, 2.40, 'successful') RETURNING id"
            ), {"location": simulator_id, "vehicle": vehicle_id, "price": price_id, "detection": detection_id, "now": now})
        command.upgrade(config, "head")
        seed.seed_demo_data()
        assert _schema(test_engine) == fresh_schema
        assert _seed_state(test_engine) == fresh_seed
        seed.seed_demo_data()
        assert _seed_state(test_engine) == fresh_seed
        with sessions() as database:
            simulator = database.get(TollLocation, simulator_id)
            traffic = database.get(TrafficRecord, traffic_id)
            price = database.get(TollPrice, price_id)
            detection = database.get(DetectionRecord, detection_id)
            transaction = database.get(TollTransaction, transaction_id)
            assert simulator.code == "SIMULATOR"
            assert {r.location_id for r in (traffic, price, detection, transaction)} == {simulator_id}
            assert price.traffic_record_id == traffic.id
            assert transaction.toll_price_id == price.id and transaction.detection_id == detection.id
            assert transaction.amount == transaction.dynamic_toll_amount == Decimal("2.40")
            assert transaction.foreign_vehicle_charge == Decimal("0.00")
            assert detection.plate_origin == "unknown" and detection.origin_reason is None
            assert detection.source == source and detection.detected_at == now
            assert detection.vehicle_id == transaction.vehicle_id == vehicle_id
            assert database.execute(text("SELECT registration_origin FROM vehicles WHERE id=:id"),
                                    {"id": vehicle_id}).scalar_one() == "malaysian"
            assert database.scalar(select(TollTransaction).where(
                TollTransaction.idempotency_key == "legacy-v3-migration"
            )).id == transaction_id

        command.downgrade(config, "20260908_0011")
        assert "foreign_vehicle_charge_settings" not in inspect(test_engine).get_table_names()
        assert "plate_origin" not in {c["name"] for c in inspect(test_engine).get_columns("detection_records")}
        with test_engine.connect() as connection:
            assert connection.scalar(text("SELECT amount FROM toll_transactions WHERE id=:id"),
                                     {"id": transaction_id}) == Decimal("2.40")
        command.upgrade(config, "head")
        assert _schema(test_engine) == fresh_schema
    finally:
        # Leave the session-scoped database clean for every other integration test.
        reset_schema()

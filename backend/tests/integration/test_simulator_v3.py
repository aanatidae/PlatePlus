"""Verify both local ALPR endpoints without physical camera/model inference."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api import webcam as webcam_api
from app.api.auth import router as auth_router
from app.db.session import get_db
from app.models import (
    Account,
    DetectionRecord,
    DynamicPricingRule,
    ForeignVehicleChargeSettings,
    TollLocation,
    TollPrice,
    TollTransaction,
    TrafficRecord,
    TrafficSimulationSettings,
    User,
    Vehicle,
)
from app.services.detection.webcam_processor import ProcessedFrame
from app.services.detection.webcam_service import WebcamService
from app.services.traffic.webcam_crossings import webcam_crossing_state
from app.services.transactions import toll_payment


def event_policy(database):
    settings = database.scalar(select(TrafficSimulationSettings))
    settings.minimum_price_change_minutes = 999
    settings.pricing_hysteresis_percentage = Decimal(50)
    settings.minimum_toll = Decimal("0.50")
    settings.maximum_toll_multiplier = Decimal("2.50")
    for rule in database.scalars(select(DynamicPricingRule)):
        rule.multiplier = {"normal": 1, "moderate": 1.5, "peak_hour": 2, "severe": 2.5}[rule.scenario]
    database.flush()


@pytest.mark.parametrize("source", ["uploaded_image", "webcam_alpr"])
@pytest.mark.parametrize("origin", ["malaysian", "singaporean"])
@pytest.mark.parametrize("prior_count,toll,category", [(3, "3.00", "moderate"), (6, "4.00", "high"), (8, "5.00", "severe")])
def test_crossing_band_price_is_persisted_before_payment(database, admin_auth_headers, monkeypatch, source, origin, prior_count, toll, category):
    from app.api import locations as location_api

    client, account, location = setup_client(database, monkeypatch, origin, "100")
    event_policy(database)
    monkeypatch.setattr(location_api, "datetime", FrozenClock)
    for index in range(prior_count):
        database.add(DetectionRecord(location_id=location.id, detected_at=NOW-timedelta(seconds=10), normalized_plate=f"PRIOR{index}", detection_confidence=.99, status="accepted", source="uploaded_image"))
    database.add(TollPrice(location_id=location.id, effective_at=NOW-timedelta(seconds=1), amount=2, congestion_category="low"))
    database.flush()
    fee = database.get(ForeignVehicleChargeSettings, "default").amount
    body = submit(client, admin_auth_headers, source, location, "repricing-arrival")
    dynamic = Decimal(toll)
    assert Decimal(str(body["payment_dynamic_toll_amount"])) == dynamic
    assert Decimal(str(body["payment_foreign_vehicle_charge"])) == (fee if origin == "singaporean" else 0)
    assert Decimal(str(body["payment_amount"])) == dynamic + (fee if origin == "singaporean" else 0)
    transaction = database.scalar(select(TollTransaction).where(TollTransaction.idempotency_key == "repricing-arrival"))
    price = database.get(TollPrice, transaction.toll_price_id)
    traffic = database.get(TrafficRecord, price.traffic_record_id)
    assert price.amount == dynamic and price.congestion_category == category
    assert traffic.vehicle_count == prior_count + 1
    assert traffic.congestion_percentage == Decimal((prior_count + 1) * 10)
    assert traffic.congestion_category == category
    database.refresh(account)
    assert account.balance == Decimal(100) - transaction.amount
    assert database.get(ForeignVehicleChargeSettings, "default").amount == fee
    app = client.app; app.include_router(location_api.router)
    live = client.get(f"/api/locations/{location.id}/live", headers=admin_auth_headers)
    assert live.status_code == 200, live.text
    assert Decimal(str(live.json()["telemetry"]["current_toll_price"])) == dynamic
    assert live.json()["telemetry"]["congestion_category"] == category
    before = counts(database)
    client.get(f"/api/locations/{location.id}/live", headers=admin_auth_headers)
    assert counts(database) == before


def test_live_read_persists_expiry_transitions_without_price_spam_or_traffic(database, admin_auth_headers, monkeypatch):
    from app.api import locations as location_api

    event_policy(database)
    location = database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))
    for index in range(7):
        database.add(DetectionRecord(location_id=location.id, detected_at=NOW-timedelta(seconds=55 if index < 2 else 10), detection_confidence=.9, status="accepted", source="webcam_alpr"))
    database.flush()
    instant = NOW
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant
    monkeypatch.setattr(location_api, "datetime", Clock)
    app = FastAPI(); app.include_router(auth_router); app.include_router(location_api.router)
    app.dependency_overrides[get_db] = lambda: database
    client = TestClient(app)
    for offset, expected_count, expected_price in [(0, 7, 4), (6, 5, 3), (61, 0, 2)]:
        instant = NOW + timedelta(seconds=offset)
        response = client.get(f"/api/locations/{location.id}/live", headers=admin_auth_headers)
        assert response.status_code == 200, response.text
        telemetry = response.json()["telemetry"]
        assert telemetry["active_crossings"] == expected_count
        assert Decimal(str(telemetry["current_toll_price"])) == expected_price
        latest = database.scalar(select(TollPrice).where(TollPrice.location_id == location.id).order_by(TollPrice.effective_at.desc(), TollPrice.created_at.desc()))
        assert latest.amount == expected_price
        price_count = database.scalar(select(func.count(TollPrice.id)))
        for _ in range(3):
            client.get(f"/api/locations/{location.id}/live", headers=admin_auth_headers)
        assert database.scalar(select(func.count(TollPrice.id))) == price_count
    assert database.scalar(select(func.count(TrafficRecord.id))) == 0
    assert database.scalar(select(func.count(TollTransaction.id))) == 0


def test_unknown_vehicle_attempt_uses_post_crossing_price_without_debit(database, admin_auth_headers, monkeypatch):
    client, account, location = setup_client(database, monkeypatch, "malaysian", "100")
    vehicle = database.scalar(select(Vehicle).where(Vehicle.plate_number == "VAA1234"))
    database.delete(vehicle)
    event_policy(database)
    for _ in range(3):
        database.add(DetectionRecord(location_id=location.id, detected_at=NOW-timedelta(seconds=10), detection_confidence=.9, status="accepted", source="uploaded_image"))
    database.flush()
    result = submit(client, admin_auth_headers, "uploaded_image", location, "repricing-unknown")
    assert result["payment_status"] == "unknown_vehicle" and result["payment_amount"] == 3
    database.refresh(account); assert account.balance == 100
    assert webcam_crossing_state(database, location, NOW)["telemetry"]["active_crossings"] == 4


def test_simulator_event_floor_and_cap_remain_enforced(database):
    from app.services.traffic.pricing import decide_price

    event_policy(database)
    location = database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))
    settings = database.scalar(select(TrafficSimulationSettings))
    settings.minimum_toll = Decimal("2.10")
    settings.maximum_toll_multiplier = Decimal(2)
    database.flush()
    assert decide_price(database, settings, location, Decimal(0), NOW, context="webcam_crossing").amount == Decimal("2.10")
    assert decide_price(database, settings, location, Decimal(90), NOW, context="webcam_crossing_expiry").amount == Decimal("4.00")

NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)


class FrozenClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz else NOW.replace(tzinfo=None)


@dataclass
class Processor:
    result: ProcessedFrame

    def process(self, raw):
        assert raw == b"local-ephemeral-input"
        return self.result


def setup_client(database, monkeypatch, origin, balance):
    plate = {"malaysian": "VAA1234", "singaporean": "GBC1234R", "unknown": "SBA1234A"}[origin]
    user = User(full_name="Synthetic Simulator Regression", email="simulator-regression@example.test")
    database.add(user)
    database.flush()
    account = Account(user_id=user.id, balance=Decimal(balance), is_primary=True)
    database.add(account)
    if origin != "unknown":
        database.add(Vehicle(user_id=user.id, plate_number=plate, registration_origin=origin))
    database.flush()
    result = ProcessedFrame(status="accepted_for_vehicle_lookup" if origin != "unknown" else "plate_origin_unsupported",
                            message="Test inference result", plate_text=plate, raw_plate_text=plate,
                            plate_origin=origin, origin_reason="ambiguous_supported_patterns" if origin == "unknown" else f"{origin}_supported_pattern",
                            detection_confidence=.99, ocr_confidence=.99, charge_eligible=origin != "unknown")
    monkeypatch.setattr(webcam_api, "service", WebcamService(Processor(result), 20, clock=lambda: 0))
    monkeypatch.setattr(webcam_api, "datetime", FrozenClock)
    monkeypatch.setattr(toll_payment, "datetime", FrozenClock)
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(webcam_api.router)
    app.dependency_overrides[get_db] = lambda: database
    return TestClient(app), account, database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))


def submit(client, headers, source, location, key):
    if source == "webcam_alpr":
        session = client.post("/api/webcam/sessions", headers=headers)
        assert session.status_code == 201, session.text
        session_id = session.json()["session_id"]
        path, field = f"/api/webcam/sessions/{session_id}/frames", "frame"
    else:
        path, field = f"/api/webcam/images?location_id={location.id}", "image"
    response = client.post(path, headers={**headers, "Idempotency-Key": key},
                           files={field: ("fixture.png", b"local-ephemeral-input", "image/png")})
    if source == "webcam_alpr":
        assert client.delete(f"/api/webcam/sessions/{session_id}", headers=headers).status_code == 204
    assert response.status_code == 200, response.text
    return response.json()


def counts(database):
    return tuple(database.scalar(select(func.count(model.id)))
                 for model in (DetectionRecord, TollTransaction, TrafficRecord, TollPrice))


@pytest.mark.parametrize("source", ["webcam_alpr", "uploaded_image"])
@pytest.mark.parametrize("origin,balance,status", [
    ("malaysian", "100", "successful"), ("singaporean", "100", "successful"),
    ("singaporean", "8", "insufficient_balance"),
])
def test_origin_and_payment_do_not_change_crossing_expiry(database, admin_auth_headers, monkeypatch, source, origin, balance, status):
    client, account, location = setup_client(database, monkeypatch, origin, balance)
    body = submit(client, admin_auth_headers, source, location, "simulator-origin-expiry")
    assert body["plate_origin"] == origin and body["payment_status"] == status
    foreign = Decimal("20.00") if origin == "singaporean" else Decimal(0)
    total = location.base_toll + foreign
    assert Decimal(str(body["payment_dynamic_toll_amount"])) == location.base_toll
    assert Decimal(str(body["payment_foreign_vehicle_charge"])) == foreign
    assert Decimal(str(body["payment_amount"])) == total
    database.refresh(account)
    assert account.balance == Decimal(balance) - (total if status == "successful" else 0)
    detection = database.scalar(select(DetectionRecord).where(DetectionRecord.location_id == location.id))
    assert detection.source == source and detection.plate_origin == origin
    assert detection.image_path is None
    before = counts(database)
    active = webcam_crossing_state(database, location, NOW + timedelta(seconds=59))["telemetry"]
    expired = webcam_crossing_state(database, location, NOW + timedelta(seconds=60))["telemetry"]
    assert active["active_crossings"] == 1 and active["congestion_percentage"] == Decimal(10)
    assert expired["active_crossings"] == 0 and expired["congestion_percentage"] == 0
    assert expired["measured_at"] == NOW + timedelta(seconds=60)
    assert expired["last_crossing_at"] == NOW
    assert active["average_speed_kmh"] is expired["average_speed_kmh"] is None
    assert counts(database) == before  # Expiry is read-only; history stays persisted.


@pytest.mark.parametrize("source", ["webcam_alpr", "uploaded_image"])
def test_unknown_origin_never_creates_a_crossing_or_debit(database, admin_auth_headers, monkeypatch, source):
    client, account, location = setup_client(database, monkeypatch, "unknown", "100")
    body = submit(client, admin_auth_headers, source, location, "simulator-unknown-origin")
    assert body["plate_origin"] == "unknown" and body["payment_status"] == "low_confidence"
    assert Decimal(str(body["payment_amount"])) == 0
    database.refresh(account)
    assert account.balance == 100
    assert webcam_crossing_state(database, location, NOW)["telemetry"]["active_crossings"] == 0
    assert database.scalar(select(func.count(TrafficRecord.id))) == 0


@pytest.mark.parametrize("source", ["webcam_alpr", "uploaded_image"])
def test_replay_and_shared_input_cooldown_preserve_all_records(database, admin_auth_headers, monkeypatch, source):
    client, account, location = setup_client(database, monkeypatch, "singaporean", "100")
    first = submit(client, admin_auth_headers, source, location, "simulator-stable-event")
    before = counts(database)
    replay = submit(client, admin_auth_headers, source, location, "simulator-stable-event")
    assert replay["payment_duplicate"] and replay["payment_amount"] == first["payment_amount"]
    assert replay["payment_foreign_vehicle_charge"] == first["payment_foreign_vehicle_charge"]
    assert counts(database) == before
    other = "uploaded_image" if source == "webcam_alpr" else "webcam_alpr"
    duplicate = submit(client, admin_auth_headers, other, location, "simulator-new-key-same-plate")
    assert duplicate["status"] == "duplicate_plate_within_cooldown"
    assert duplicate["payment_status"] is None
    assert counts(database) == before
    database.refresh(account)
    assert account.balance == Decimal(100) - Decimal(str(first["payment_amount"]))

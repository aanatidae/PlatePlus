"""Policy saves immediately propagate through persisted prices, telemetry and charging."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.locations import _state
from app.models import Account, DetectionRecord, DynamicPricingRule, ForeignVehicleChargeSettings, OperationalEvent, TollLocation, TollPrice, TollTransaction, TrafficRecord, TrafficSimulationSettings, User, Vehicle
from app.services.demo_feed import generate_crossing
from app.services.transactions.toll_payment import process_toll_event


def payload(database, *, moderate="2.00", low_max="30.00"):
    rules = list(database.scalars(select(DynamicPricingRule).order_by(DynamicPricingRule.minimum_percentage)))
    result = [{key: str(getattr(rule, key)) for key in ("scenario", "minimum_percentage", "maximum_percentage", "multiplier")} for rule in rules]
    result[0]["maximum_percentage"] = low_max
    result[1]["minimum_percentage"] = str(Decimal(low_max) + Decimal("0.01"))
    result[1]["multiplier"] = moderate
    return {"rules": result}


def latest(database, location):
    return database.scalar(select(TollPrice).where(TollPrice.location_id == location.id).order_by(TollPrice.effective_at.desc()))


def traffic_and_price(database, location, congestion="35.00", category="moderate", multiplier="1.50"):
    now = datetime.now(UTC) - timedelta(seconds=1)
    traffic = TrafficRecord(location_id=location.id, measured_at=now, vehicle_count=35,
        road_capacity=location.road_capacity, congestion_percentage=Decimal(congestion),
        congestion_category=category, scenario="moderate", source="manual")
    database.add(traffic); database.flush()
    price = TollPrice(location_id=location.id, traffic_record_id=traffic.id, effective_at=now,
        amount=location.base_toll * Decimal(multiplier), congestion_category=category)
    database.add(price); database.flush()
    return traffic, price


def vehicle(database, *, plate="VAA1234", origin="malaysian"):
    user = User(full_name="Synthetic Policy Test", email=f"{plate}@example.test")
    database.add(user); database.flush()
    account = Account(user_id=user.id, balance=Decimal("1000"), is_primary=True)
    car = Vehicle(user_id=user.id, plate_number=plate, registration_origin=origin)
    database.add_all([account, car]); database.flush()
    return car


def cross(database, location, car, key):
    return process_toll_event(database, location_id=location.id, idempotency_key=key,
        normalized_plate=car.plate_number, raw_plate_text=car.plate_number,
        detection_confidence=.99, ocr_confidence=.99, recognition_accepted=True, source="demo_generated")


def save(database, database_app, headers, **changes):
    response = TestClient(database_app).put("/api/traffic/pricing-rules", headers=headers, json=payload(database, **changes))
    assert response.status_code == 200, response.text


def test_policy_reprices_all_locations_without_traffic_changes(database, database_app, admin_auth_headers):
    locations = list(database.scalars(select(TollLocation).where(TollLocation.code != "SIMULATOR").order_by(TollLocation.code)))
    states = [("25", "low", "1"), ("35", "moderate", "1.5"), ("70", "high", "2"), ("90", "severe", "2.5")]
    old = [traffic_and_price(database, location, *state) for location, state in zip(locations, states)]
    before = database.scalar(select(func.count(TrafficRecord.id)))
    save(database, database_app, admin_auth_headers)
    for location, state, (traffic, price) in zip(locations, states, old):
        updated = latest(database, location)
        expected_multiplier = Decimal("2") if state[1] == "moderate" else Decimal(state[2])
        assert updated.amount == location.base_toll * expected_multiplier
        assert updated.id != price.id
        assert updated.traffic_record_id == traffic.id
        assert traffic.congestion_percentage == Decimal(state[0])
        assert _state(database, location)["telemetry"]["current_toll_price"] == updated.amount
        assert price.amount == location.base_toll * Decimal(state[2])
    assert database.scalar(select(func.count(TrafficRecord.id))) == before


def test_new_payments_and_running_feed_use_new_price_history_is_immutable(database, database_app, admin_auth_headers):
    location = database.scalar(select(TollLocation).where(TollLocation.code == "PENCHALA"))
    traffic, old_price = traffic_and_price(database, location)
    car = vehicle(database)
    assert cross(database, location, car, "before-policy").amount == Decimal("3.00")
    history = database.scalar(select(TollTransaction).where(TollTransaction.idempotency_key == "before-policy"))
    stale_telemetry = _state(database, location)["telemetry"]
    save(database, database_app, admin_auth_headers)
    assert latest(database, location).amount == Decimal("4.00")
    assert cross(database, location, car, "after-policy-1").amount == Decimal("4.00")
    assert cross(database, location, car, "after-policy-2").amount == Decimal("4.00")
    # A feed crossing already holding an older snapshot cannot overwrite the policy price.
    assert generate_crossing(database, location, stale_telemetry, vehicle=car) == "successful"
    feed_payment = database.scalar(select(TollTransaction).where(TollTransaction.idempotency_key.like("demo-feed:%")).order_by(TollTransaction.processed_at.desc()))
    assert feed_payment.dynamic_toll_amount == Decimal("4.00")
    database.refresh(history); database.refresh(old_price); database.refresh(traffic)
    assert history.amount == Decimal("3.00") and history.toll_price_id == old_price.id
    assert old_price.amount == Decimal("3.00") and traffic.congestion_percentage == Decimal("35.00")
    sg = vehicle(database, plate="GBC6427R", origin="singaporean")
    charge = database.get(ForeignVehicleChargeSettings, "default").amount
    result = cross(database, location, sg, "sg-after-policy")
    assert result.dynamic_toll_amount == Decimal("4.00")
    assert result.foreign_vehicle_charge == charge
    assert result.amount == Decimal("4.00") + charge


def test_boundary_change_reclassifies_live_band_but_preserves_measurement(database, database_app, admin_auth_headers):
    location = database.scalar(select(TollLocation).where(TollLocation.code == "PENCHALA"))
    traffic, old_price = traffic_and_price(database, location)
    settings = database.scalar(select(TrafficSimulationSettings))
    settings.minimum_price_change_minutes = 120
    settings.pricing_hysteresis_percentage = Decimal("20")
    save(database, database_app, admin_auth_headers, low_max="40.00")
    state = TestClient(database_app).get(f"/api/locations/{location.id}/live", headers=admin_auth_headers)
    assert state.status_code == 200
    live = state.json()["telemetry"]
    assert Decimal(str(live["congestion_percentage"])) == Decimal("35")
    assert live["congestion_category"] == "low"
    assert Decimal(str(live["current_toll_price"])) == Decimal("2")
    assert latest(database, location).congestion_category == "low"
    assert traffic.congestion_category == "moderate" and old_price.congestion_category == "moderate"


def test_policy_reprices_real_simulator_crossings_without_creating_traffic(database, database_app, admin_auth_headers):
    location = database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))
    stale_traffic, _ = traffic_and_price(database, location, "10", "low", "1")
    now = datetime.now(UTC)
    for index in range(5):
        database.add(DetectionRecord(location_id=location.id, detected_at=now, status="accepted",
            source="webcam_alpr" if index % 2 else "uploaded_image", detection_confidence=.99))
    database.flush()
    count = database.scalar(select(func.count(DetectionRecord.id)))
    traffic_count = database.scalar(select(func.count(TrafficRecord.id)))
    save(database, database_app, admin_auth_headers)
    live = _state(database, location)["telemetry"]
    assert live["active_crossings"] == 5 and live["congestion_percentage"] == Decimal("50")
    assert live["current_toll_price"] == location.base_toll * Decimal("2")
    assert latest(database, location).amount == live["current_toll_price"]
    assert latest(database, location).traffic_record_id is None
    assert database.scalar(select(func.count(DetectionRecord.id))) == count
    assert database.scalar(select(func.count(TrafficRecord.id))) == traffic_count
    assert stale_traffic.congestion_percentage == Decimal("10")


def test_repeated_policy_save_does_not_spam_price_change_events(database, database_app, admin_auth_headers):
    save(database, database_app, admin_auth_headers)
    count = database.scalar(select(func.count(OperationalEvent.id)).where(OperationalEvent.event_type == "pricing_change"))
    save(database, database_app, admin_auth_headers)
    assert database.scalar(select(func.count(OperationalEvent.id)).where(OperationalEvent.event_type == "pricing_change")) == count

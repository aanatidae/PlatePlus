from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import (
    Account,
    DetectionRecord,
    TollLocation,
    TollPrice,
    TollTransaction,
    TrafficRecord,
    TrafficSimulationSettings,
)


def state(database):
    return {
        "counts": [
            database.scalar(select(func.count()).select_from(model))
            for model in [TollPrice, TrafficRecord, DetectionRecord, TollTransaction]
        ],
        "balances": [
            item.balance for item in database.scalars(select(Account).order_by(Account.id))
        ],
    }


def test_preview_10_and_90_use_entered_congestion_and_do_not_write(
    database, database_app, admin_auth_headers
):
    location = database.scalar(select(TollLocation).where(TollLocation.code == "AKLEH"))
    location.base_toll = Decimal("2.40")
    database.add(
        TollPrice(
            location_id=location.id,
            effective_at=datetime.now(UTC) - timedelta(minutes=10),
            amount=Decimal("2.40"),
            congestion_category="low",
        )
    )
    database.commit()
    before = state(database)
    client = TestClient(database_app)
    results = [
        client.get(
            "/api/traffic/pricing-preview",
            params={"location_id": str(location.id), "congestion_percentage": value},
            headers=admin_auth_headers,
        )
        for value in [10, 90]
    ]
    assert [result.status_code for result in results] == [200, 200]
    low, high = [result.json() for result in results]
    assert Decimal(str(low["congestion_percentage"])) == 10
    assert Decimal(str(high["congestion_percentage"])) == 90
    assert (low["congestion_category"], high["congestion_category"]) == ("low", "severe")
    assert (Decimal(str(low["multiplier"])), Decimal(str(high["multiplier"]))) == (1, Decimal("2.5"))
    assert (Decimal(str(low["new_toll"])), Decimal(str(high["new_toll"]))) == (
        Decimal("2.40"),
        Decimal("6.00"),
    )
    assert Decimal(str(high["previous_toll"])) == Decimal("2.40")
    assert state(database) == before
    assert (
        client.get(
            "/api/traffic/pricing-preview",
            params={"location_id": str(location.id), "congestion_percentage": 101},
            headers=admin_auth_headers,
        ).status_code
        == 422
    )
    assert client.get(
        "/api/traffic/pricing-preview",
        params={"location_id": str(location.id), "congestion_percentage": "30.005"},
        headers=admin_auth_headers,
    ).status_code == 422


def test_preview_explains_interval_hold_and_limit_without_writing(
    database, database_app, admin_auth_headers
):
    location = database.scalar(select(TollLocation).where(TollLocation.code == "AKLEH"))
    location.base_toll = Decimal("2.40")
    policy = database.scalar(select(TrafficSimulationSettings))
    policy.minimum_price_change_minutes = 5
    price = TollPrice(
        location_id=location.id,
        effective_at=datetime.now(UTC),
        amount=Decimal("2.40"),
        congestion_category="low",
    )
    database.add(price)
    database.commit()
    client = TestClient(database_app)
    path = f"/api/traffic/pricing-preview?location_id={location.id}&congestion_percentage=90"
    before = state(database)
    held = client.get(path, headers=admin_auth_headers).json()
    assert held["reason"] == "minimum change interval hold"
    assert Decimal(str(held["new_toll"])) == Decimal("2.40")
    assert state(database) == before
    price.effective_at = datetime.now(UTC) - timedelta(minutes=10)
    policy.maximum_toll_multiplier = Decimal("1.50")
    database.commit()
    before = state(database)
    limited = client.get(path, headers=admin_auth_headers).json()
    assert "maximum multiplier cap applied" in limited["reason"]
    assert Decimal(str(limited["new_toll"])) == Decimal("3.60")
    assert state(database) == before


def test_feed_reports_recovery_and_reset_waits_for_worker(
    database_app, admin_auth_headers, monkeypatch
):
    fake = SimpleNamespace(
        status=lambda: {
            "running": True,
            "state": "recovering",
            "last_error": "ConnectionError: retrying automatically",
        },
        pause=lambda: True,
        worker_alive=True,
    )
    monkeypatch.setattr("app.api.operations.demo_feed", fake)
    client = TestClient(database_app)
    status = client.get("/api/operations/demo/feed", headers=admin_auth_headers).json()
    assert status["state"] == "recovering" and status["running"]
    response = client.post("/api/operations/demo/feed/reset", headers=admin_auth_headers)
    assert response.status_code == 409
    assert "in-flight cycle" in response.json()["detail"]

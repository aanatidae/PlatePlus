from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import (
    Account,
    AdminAuditLog,
    DetectionRecord,
    ForeignVehicleChargeSettings,
    PaymentNotification,
    TollLocation,
    TollPrice,
    TollTransaction,
    User,
    Vehicle,
    WalletLedgerEntry,
)
from app.services.transactions.toll_payment import process_toll_event


def _seed_registered_vehicle(
    database, *, balance: Decimal = Decimal("20.00"), is_primary: bool = True,
    plate_number: str = "VAA1234", registration_origin: str = "malaysian",
) -> tuple[Account, Vehicle]:
    user = User(full_name="Payment Test User", email="payment@example.test")
    database.add(user)
    database.flush()
    account = Account(user_id=user.id, balance=balance, is_primary=is_primary)
    vehicle = Vehicle(user_id=user.id, plate_number=plate_number, registration_origin=registration_origin)
    database.add_all([account, vehicle])
    database.flush()
    return account, vehicle


def _seed_current_price(database, amount: Decimal = Decimal("2.00")) -> TollPrice:
    price = TollPrice(
        effective_at=datetime.now(UTC) - timedelta(minutes=1),
        amount=amount,
        congestion_category="low",
    )
    database.add(price)
    database.flush()
    return price


def _process(database, key: str, **overrides):
    payload = {
        "idempotency_key": key,
        "raw_plate_text": "VAA 1234",
        "normalized_plate": "VAA1234",
        "detection_confidence": 0.95,
        "ocr_confidence": 0.93,
        "recognition_accepted": True,
    }
    payload.update(overrides)
    return process_toll_event(database, **payload)


def test_successful_payment_debits_the_primary_account(database) -> None:
    account, vehicle = _seed_registered_vehicle(database)
    price = _seed_current_price(database)

    outcome = _process(database, "payment-success-0001")

    database.refresh(account)
    transaction = database.scalar(select(TollTransaction))
    detection = database.scalar(select(DetectionRecord))
    assert outcome.status == "successful"
    assert outcome.amount == Decimal("2.00")
    assert outcome.dynamic_toll_amount == Decimal("2.00")
    assert outcome.foreign_vehicle_charge == Decimal("0.00")
    assert account.balance == Decimal("18.00")
    assert transaction is not None
    assert transaction.account_id == account.id
    assert transaction.vehicle_id == vehicle.id
    assert transaction.toll_price_id == price.id
    assert transaction.dynamic_toll_amount == Decimal("2.00")
    assert transaction.foreign_vehicle_charge == Decimal("0.00")
    assert detection is not None
    assert detection.status == "accepted"
    assert detection.plate_origin == "malaysian"
    assert detection.origin_reason == "malaysian_supported_pattern"
    assert detection.vehicle_id == vehicle.id
    ledger = database.scalar(select(WalletLedgerEntry))
    assert ledger is not None
    assert ledger.entry_type == "toll_deduction"
    assert ledger.balance_after == Decimal("18.00")
    assert database.scalar(select(PaymentNotification)) is not None


def test_insufficient_balance_does_not_debit_the_primary_account(database) -> None:
    account, _ = _seed_registered_vehicle(database, balance=Decimal("1.50"))
    _seed_current_price(database)

    outcome = _process(database, "payment-insufficient-0001")

    database.refresh(account)
    transaction = database.scalar(select(TollTransaction))
    assert outcome.status == "insufficient_balance"
    assert account.balance == Decimal("1.50")
    assert transaction is not None
    assert transaction.balance_after == Decimal("1.50")
    assert transaction.failure_reason == "The primary simulated account has insufficient balance."


def test_unknown_vehicle_is_recorded_without_a_deduction(database) -> None:
    _seed_current_price(database)

    outcome = _process(database, "payment-unknown-0001", normalized_plate="ZZZ9999")

    detection = database.scalar(select(DetectionRecord))
    transaction = database.scalar(select(TollTransaction))
    assert outcome.status == "unknown_vehicle"
    assert detection is not None
    assert detection.status == "unknown_vehicle"
    assert detection.vehicle_id is None
    assert transaction is not None
    assert transaction.amount == Decimal("2.00")
    assert transaction.account_id is None


def test_low_confidence_recognition_is_recorded_without_a_price_or_deduction(database) -> None:
    account, _ = _seed_registered_vehicle(database)

    outcome = _process(
        database,
        "payment-low-confidence-0001",
        recognition_accepted=False,
        ocr_confidence=0.2,
    )

    database.refresh(account)
    transaction = database.scalar(select(TollTransaction))
    detection = database.scalar(select(DetectionRecord))
    assert outcome.status == "low_confidence"
    assert account.balance == Decimal("20.00")
    assert detection is not None
    assert detection.status == "low_confidence"
    assert detection.review_status == "pending"
    assert transaction is not None
    assert transaction.amount == Decimal("0.00")


def test_missing_current_price_fails_without_a_deduction(database) -> None:
    account, _ = _seed_registered_vehicle(database)

    outcome = _process(database, "payment-no-price-0001")

    database.refresh(account)
    transaction = database.scalar(select(TollTransaction))
    assert outcome.status == "failed"
    assert account.balance == Decimal("20.00")
    assert transaction is not None
    assert transaction.failure_reason == "No current simulated toll price is available."


def test_repeated_idempotency_key_returns_the_original_result_without_another_debit(database) -> None:
    account, _ = _seed_registered_vehicle(database)
    _seed_current_price(database)

    first = _process(database, "payment-idempotent-0001")
    second = _process(database, "payment-idempotent-0001")

    database.refresh(account)
    transactions = list(database.scalars(select(TollTransaction)))
    assert first.status == "successful"
    assert second.status == "successful"
    assert second.duplicate is True
    assert second.transaction_id == first.transaction_id
    assert account.balance == Decimal("18.00")
    assert len(transactions) == 1


def test_ambiguous_origin_is_persisted_and_never_debits(database) -> None:
    account, _ = _seed_registered_vehicle(database, plate_number="SLP1234A")
    _seed_current_price(database)

    outcome = _process(database, "payment-ambiguous-0001", normalized_plate="SLP1234A")

    database.refresh(account)
    detection = database.scalar(select(DetectionRecord))
    assert outcome.status == "low_confidence"
    assert account.balance == Decimal("20.00")
    assert detection.plate_origin == "unknown"
    assert detection.origin_reason == "ambiguous_supported_patterns"


def test_singaporean_payment_adds_configured_foreign_charge_once(database) -> None:
    account, _ = _seed_registered_vehicle(database, balance=Decimal("30.00"), plate_number="GBC1234R", registration_origin="singaporean")
    _seed_current_price(database)
    database.get(ForeignVehicleChargeSettings, "default").amount = Decimal("7.50")

    outcome = _process(database, "payment-sg-0001", normalized_plate="GBC1234R")
    duplicate = _process(database, "payment-sg-0001", normalized_plate="GBC1234R")

    database.refresh(account)
    detection = database.scalar(select(DetectionRecord))
    transaction = database.scalar(select(TollTransaction))
    assert outcome.status == "successful"
    assert outcome.amount == Decimal("9.50")
    assert outcome.dynamic_toll_amount == Decimal("2.00")
    assert outcome.foreign_vehicle_charge == Decimal("7.50")
    assert duplicate.duplicate is True
    assert duplicate.amount == outcome.amount
    assert account.balance == Decimal("20.50")
    assert transaction.dynamic_toll_amount + transaction.foreign_vehicle_charge == transaction.amount
    assert database.scalar(select(WalletLedgerEntry)).amount == Decimal("9.50")
    assert "RM9.50" in database.scalar(select(PaymentNotification)).message
    assert detection.plate_origin == "singaporean"
    assert detection.origin_reason == "singaporean_supported_pattern"


def test_singaporean_insufficient_balance_uses_final_total(database) -> None:
    account, _ = _seed_registered_vehicle(database, balance=Decimal("20.00"), plate_number="GBC1234R", registration_origin="singaporean")
    _seed_current_price(database)

    outcome = _process(database, "payment-sg-low-balance-0001", normalized_plate="GBC1234R")

    database.refresh(account)
    transaction = database.scalar(select(TollTransaction))
    assert outcome.status == "insufficient_balance"
    assert account.balance == Decimal("20.00")
    assert transaction.dynamic_toll_amount == Decimal("2.00")
    assert transaction.foreign_vehicle_charge == Decimal("20.00")
    assert transaction.amount == Decimal("22.00")
    assert database.scalar(select(WalletLedgerEntry)) is None


def test_registered_origin_mismatch_fails_without_debit(database) -> None:
    account, _ = _seed_registered_vehicle(database, plate_number="GBC1234R")
    _seed_current_price(database)

    outcome = _process(database, "payment-sg-mismatch-0001", normalized_plate="GBC1234R")

    database.refresh(account)
    assert outcome.status == "failed"
    assert account.balance == Decimal("20.00")
    assert database.scalar(select(TollTransaction)).failure_reason.startswith("Recognized plate origin")


def test_missing_foreign_charge_configuration_fails_singaporean_payment_safely(database) -> None:
    account, _ = _seed_registered_vehicle(database, balance=Decimal("40.00"), plate_number="GBC1234R", registration_origin="singaporean")
    _seed_current_price(database)
    database.delete(database.get(ForeignVehicleChargeSettings, "default"))
    database.flush()

    outcome = _process(database, "payment-sg-no-config-0001", normalized_plate="GBC1234R")

    database.refresh(account)
    assert outcome.status == "failed"
    assert account.balance == Decimal("40.00")
    assert database.scalar(select(WalletLedgerEntry)) is None
    assert "not configured" in database.scalar(select(TollTransaction)).failure_reason


def test_foreign_charge_configuration_and_reversal_use_final_debit(database, database_app, admin_auth_headers) -> None:
    account, _ = _seed_registered_vehicle(database, balance=Decimal("40.00"), plate_number="GBC1234R", registration_origin="singaporean")
    _seed_current_price(database)
    client = TestClient(database_app)
    response = client.put(
        "/api/data/foreign-vehicle-charge", json={"amount": "6.25"}, headers=admin_auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["amount"] == "6.25"
    assert database.scalar(select(AdminAuditLog).where(AdminAuditLog.action == "foreign_vehicle_charge_updated")) is not None

    outcome = _process(database, "payment-sg-reversal-0001", normalized_plate="GBC1234R")
    assert outcome.amount == Decimal("8.25")
    transaction_response = client.get("/api/data/transactions", headers=admin_auth_headers)
    assert transaction_response.status_code == 200, transaction_response.text
    assert transaction_response.json()[0]["foreign_vehicle_charge"] == "6.25"
    reversal = client.post(
        f"/api/data/transactions/{outcome.transaction_id}/reversal",
        json={"reason": "Synthetic demonstration refund", "idempotency_key": "payment-sg-reversal-key"},
        headers=admin_auth_headers,
    )
    assert reversal.status_code == 200, reversal.text
    database.refresh(account)
    assert account.balance == Decimal("40.00")
    ledger = list(database.scalars(select(WalletLedgerEntry).order_by(WalletLedgerEntry.created_at)))
    assert {entry.entry_type: entry.amount for entry in ledger} == {
        "toll_deduction": Decimal("8.25"), "reversal": Decimal("8.25"),
    }


def test_only_the_designated_primary_account_is_used(database) -> None:
    primary, _ = _seed_registered_vehicle(database, balance=Decimal("7.00"))
    secondary = Account(user_id=primary.user_id, balance=Decimal("50.00"), is_primary=False)
    database.add(secondary)
    database.flush()
    _seed_current_price(database)

    outcome = _process(database, "payment-primary-0001")

    database.refresh(primary)
    database.refresh(secondary)
    assert outcome.status == "successful"
    assert primary.balance == Decimal("5.00")
    assert secondary.balance == Decimal("50.00")


@pytest.mark.parametrize("code", ["LDP", "AKLEH", "NPE", "GRAND_SAGA"])
def test_singaporean_payment_and_api_history_keep_selected_location(
    database, database_app, admin_auth_headers, code,
):
    account, _ = _seed_registered_vehicle(
        database, balance=Decimal("100.00"), plate_number="GBC1234R",
        registration_origin="singaporean",
    )
    locations = list(database.scalars(select(TollLocation).where(TollLocation.status != "retired")))
    selected = next(location for location in locations if location.code == code)
    for index, location in enumerate(locations):
        database.add(TollPrice(
            location_id=location.id, amount=Decimal(index + 1),
            effective_at=datetime.now(UTC) - timedelta(minutes=1), congestion_category="low",
        ))
    database.flush()
    current = database.scalar(select(TollPrice).where(TollPrice.location_id == selected.id))
    expected = current.amount + Decimal("20.00")
    outcome = _process(database, f"sg-location-{code}", normalized_plate="GBC1234R", location_id=selected.id)
    assert outcome.status == "successful" and outcome.amount == expected
    database.refresh(account)
    assert account.balance == Decimal("100.00") - expected
    client = TestClient(database_app)
    for resource in ("detections", "transactions"):
        response = client.get(f"/api/data/{resource}", params={"location_id": str(selected.id)}, headers=admin_auth_headers)
        assert response.status_code == 200, response.text
        assert len(response.json()) == 1
        record = response.json()[0]
        assert record["location_id"] == str(selected.id)
        if resource == "detections":
            assert record["plate_origin"] == "singaporean"
            assert record["origin_reason"] == "singaporean_supported_pattern"
        else:
            assert Decimal(record["dynamic_toll_amount"]) == current.amount
            assert Decimal(record["foreign_vehicle_charge"]) == Decimal("20.00")
            assert Decimal(record["amount"]) == expected
        other = next(location for location in locations if location.id != selected.id)
        scoped = client.get(f"/api/data/{resource}", params={"location_id": str(other.id)}, headers=admin_auth_headers)
        assert scoped.status_code == 200 and scoped.json() == []

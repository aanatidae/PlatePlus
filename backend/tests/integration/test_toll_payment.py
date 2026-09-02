from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models import Account, DetectionRecord, TollPrice, TollTransaction, User, Vehicle
from app.services.transactions.toll_payment import process_toll_event


def _seed_registered_vehicle(
    database, *, balance: Decimal = Decimal("20.00"), is_primary: bool = True
) -> tuple[Account, Vehicle]:
    user = User(full_name="Payment Test User", email="payment@example.test")
    database.add(user)
    database.flush()
    account = Account(user_id=user.id, balance=balance, is_primary=is_primary)
    vehicle = Vehicle(user_id=user.id, plate_number="VAA1234")
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
    assert account.balance == Decimal("18.00")
    assert transaction is not None
    assert transaction.account_id == account.id
    assert transaction.vehicle_id == vehicle.id
    assert transaction.toll_price_id == price.id
    assert detection is not None
    assert detection.status == "accepted"
    assert detection.vehicle_id == vehicle.id


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

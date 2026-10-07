"""Country-specific payment safety without a PostgreSQL dependency."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from alpr.plate.origin import classify_plate_origin

from app.models import TollTransaction, WalletLedgerEntry
from app.services.transactions.toll_payment import process_toll_event


@pytest.mark.parametrize("plate,origin", [
    ("VAA1234", "malaysian"), ("GBC1234R", "singaporean"),
    ("SLP1234A", "unknown"), ("1234", "unknown"),
])
def test_backend_origin_contract(plate, origin):
    assert classify_plate_origin(plate).origin == origin


@pytest.mark.parametrize("plate,origin,fee,balance,status,total", [
    ("VAA1234", "malaysian", "20.00", "10.00", "successful", "2.40"),
    ("GBC1234R", "singaporean", "6.25", "8.65", "successful", "8.65"),
    ("GBC1234R", "singaporean", "6.25", "8.64", "insufficient_balance", "8.65"),
    ("GBC1234R", "singaporean", "0.00", "2.40", "successful", "2.40"),
])
def test_country_charge_checks_and_debits_the_combined_total(
    plate, origin, fee, balance, status, total,
):
    location_id = uuid4()
    account = SimpleNamespace(id=uuid4(), balance=Decimal(balance))
    vehicle = SimpleNamespace(id=uuid4(), user_id=uuid4(), registration_origin=origin)
    price = SimpleNamespace(id=uuid4(), amount=Decimal("2.40"))
    database = Mock()
    database.scalar.side_effect = [None, price, vehicle, account]
    database.get.return_value = SimpleNamespace(amount=Decimal(fee))

    outcome = process_toll_event(
        database, idempotency_key="unit-v3-country", raw_plate_text=plate,
        normalized_plate=plate, detection_confidence=.99, ocr_confidence=.99,
        recognition_accepted=True, location_id=location_id,
    )

    assert outcome.status == status
    assert outcome.amount == Decimal(total)
    assert outcome.dynamic_toll_amount == Decimal("2.40")
    assert outcome.foreign_vehicle_charge == (Decimal(fee) if origin == "singaporean" else 0)
    records = [call.args[0] for call in database.add.call_args_list]
    transaction = next(row for row in records if isinstance(row, TollTransaction))
    assert transaction.location_id == location_id
    assert transaction.amount == transaction.dynamic_toll_amount + transaction.foreign_vehicle_charge
    ledger = [row for row in records if isinstance(row, WalletLedgerEntry)]
    if status == "successful":
        assert account.balance == Decimal(balance) - Decimal(total)
        assert len(ledger) == 1 and ledger[0].amount == Decimal(total)
    else:
        assert account.balance == Decimal(balance)
        assert ledger == []
    if origin == "malaysian":
        database.get.assert_not_called()

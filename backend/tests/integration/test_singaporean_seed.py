"""The local seed adds fictional SG vehicles without changing existing wallets."""

from contextlib import nullcontext
from decimal import Decimal

from sqlalchemy import func, select

from app.db import seed
from app.models import Account, User, Vehicle, WalletLedgerEntry
from app.services.transactions.toll_payment import process_toll_event


def test_singaporean_seed_is_idempotent_and_keeps_synthetic_balances(database, monkeypatch) -> None:
    class TestSessionLocal:
        @staticmethod
        def begin():
            return nullcontext(database)

    monkeypatch.setattr(seed, "SessionLocal", TestSessionLocal)
    seed.seed_demo_data()
    database.flush()
    before = (
        database.scalar(select(func.count(User.id))),
        database.scalar(select(func.count(Account.id))),
        database.scalar(select(func.count(Vehicle.id))),
        database.scalar(select(func.count(WalletLedgerEntry.id))),
    )
    seed.seed_demo_data()
    database.flush()
    after = (
        database.scalar(select(func.count(User.id))),
        database.scalar(select(func.count(Account.id))),
        database.scalar(select(func.count(Vehicle.id))),
        database.scalar(select(func.count(WalletLedgerEntry.id))),
    )
    assert before == after == (99, 99, 99, 99)

    for person in seed.synthetic_singaporean_demo_people():
        _, email, _, plate, *_ = person
        user = database.scalar(select(User).where(User.email == email))
        vehicle = database.scalar(select(Vehicle).where(Vehicle.plate_number == plate))
        account = database.scalar(select(Account).where(Account.user_id == user.id))
        assert vehicle.user_id == user.id
        assert vehicle.registration_origin == "singaporean"
        assert account.is_primary and account.balance == Decimal(person[-1])

    def cross(plate: str, key: str):
        return process_toll_event(
            database, idempotency_key=key, raw_plate_text=plate, normalized_plate=plate,
            detection_confidence=0.99, ocr_confidence=0.99, recognition_accepted=True,
        )

    successful = cross("GBC6427R", "seeded-sg-success-0001")
    insufficient = cross("YN4821R", "seeded-sg-insufficient-0001")
    assert successful.status == "successful"
    assert successful.foreign_vehicle_charge == Decimal("20.00")
    assert insufficient.status == "insufficient_balance"

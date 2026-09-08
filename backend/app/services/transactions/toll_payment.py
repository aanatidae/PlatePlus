"""Atomic simulated toll-payment workflow for recognized number plates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    DetectionRecord,
    PaymentNotification,
    TollPrice,
    TollTransaction,
    Vehicle,
    WalletLedgerEntry,
)
from app.services.locations import default_toll_location_id


@dataclass(frozen=True)
class PaymentOutcome:
    status: str
    message: str
    amount: Decimal
    balance_after: Decimal | None
    transaction_id: str | None
    duplicate: bool = False


def recognition_is_charge_eligible(
    recognition_accepted: bool, normalized_plate: str | None
) -> bool:
    """Return whether a recognition can enter the simulated payment workflow."""
    return recognition_accepted and bool(normalized_plate)


def has_sufficient_balance(balance: Decimal, amount: Decimal) -> bool:
    """Return whether a simulated account can cover a toll without overdrafting."""
    return balance >= amount


def balance_after_toll(balance: Decimal, amount: Decimal) -> Decimal:
    """Deduct a covered simulated toll, rejecting any overdraft attempt."""
    if not has_sufficient_balance(balance, amount):
        raise ValueError("Simulated account balance is insufficient for this toll.")
    return balance - amount


def process_toll_event(
    database: Session,
    *,
    idempotency_key: str,
    raw_plate_text: str | None,
    normalized_plate: str | None,
    detection_confidence: float | None,
    ocr_confidence: float | None,
    recognition_accepted: bool,
    source: str = "webcam",
    detected_at: datetime | None = None,
    location_id: UUID | None = None,
) -> PaymentOutcome:
    """Persist one recognition event and deduct only once when it is eligible."""
    existing = database.scalar(
        select(TollTransaction).where(TollTransaction.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return PaymentOutcome(
            existing.status,
            "This simulated toll event was already processed.",
            existing.amount,
            existing.balance_after,
            str(existing.id),
            duplicate=True,
        )

    now = detected_at or datetime.now(UTC)
    location_id = location_id or default_toll_location_id(database)
    detection = DetectionRecord(
        location_id=location_id,
        detected_at=now,
        raw_plate_text=raw_plate_text,
        normalized_plate=normalized_plate,
        detection_confidence=Decimal(str(detection_confidence or 0)),
        ocr_confidence=Decimal(str(ocr_confidence)) if ocr_confidence is not None else None,
        status="accepted" if recognition_accepted and normalized_plate else "low_confidence",
        review_status="not_required" if recognition_accepted and normalized_plate else "pending",
        source=source,
    )
    database.add(detection)
    database.flush()

    price = database.scalar(
        select(TollPrice)
        .where(TollPrice.location_id == location_id, TollPrice.effective_at <= now)
        .order_by(TollPrice.effective_at.desc())
        .limit(1)
    )
    if not recognition_is_charge_eligible(recognition_accepted, normalized_plate):
        return _record_failure(
            database,
            detection,
            idempotency_key,
            now,
            "low_confidence",
            "Recognition did not pass confidence checks.",
        )
    if price is None:
        detection.status = "error"
        return _record_failure(
            database,
            detection,
            idempotency_key,
            now,
            "failed",
            "No current simulated toll price is available.",
        )

    vehicle = database.scalar(
        select(Vehicle).where(Vehicle.plate_number == normalized_plate, Vehicle.is_active.is_(True))
    )
    if vehicle is None:
        detection.status = "unknown_vehicle"
        return _record_failure(
            database,
            detection,
            idempotency_key,
            now,
            "unknown_vehicle",
            "The recognized plate is not registered to an active simulated vehicle.",
            price=price,
        )

    detection.vehicle_id = vehicle.id
    account = database.scalar(
        select(Account)
        .where(
            Account.user_id == vehicle.user_id,
            Account.is_active.is_(True),
            Account.is_primary.is_(True),
        )
        .with_for_update()
    )
    if account is None:
        detection.status = "error"
        return _record_failure(
            database,
            detection,
            idempotency_key,
            now,
            "failed",
            "The vehicle owner has no active primary simulated account.",
            vehicle=vehicle,
            price=price,
        )
    if not has_sufficient_balance(account.balance, price.amount):
        detection.status = "accepted"
        return _record_failure(
            database,
            detection,
            idempotency_key,
            now,
            "insufficient_balance",
            "The primary simulated account has insufficient balance.",
            account=account,
            vehicle=vehicle,
            price=price,
        )

    account.balance = balance_after_toll(account.balance, price.amount)
    transaction = TollTransaction(
        location_id=location_id,
        account_id=account.id,
        vehicle_id=vehicle.id,
        toll_price_id=price.id,
        detection_id=detection.id,
        idempotency_key=idempotency_key,
        processed_at=now,
        amount=price.amount,
        status="successful",
        balance_after=account.balance,
    )
    database.add(transaction)
    database.flush()
    _add_wallet_entry(
        database, account, transaction, "toll_deduction", price.amount, "debit",
        f"Simulated toll deduction at {location_id}.", f"toll:{idempotency_key}",
    )
    _add_notification(
        database, vehicle.user_id, transaction, "payment_success",
        f"Simulated toll payment of RM{price.amount:.2f} was processed.",
    )
    database.commit()
    database.refresh(transaction)
    return PaymentOutcome(
        "successful",
        "Simulated toll payment was processed.",
        transaction.amount,
        transaction.balance_after,
        str(transaction.id),
    )


def _record_failure(
    database: Session,
    detection: DetectionRecord,
    idempotency_key: str,
    processed_at: datetime,
    status: str,
    message: str,
    *,
    account: Account | None = None,
    vehicle: Vehicle | None = None,
    price: TollPrice | None = None,
) -> PaymentOutcome:
    transaction = TollTransaction(
        location_id=detection.location_id,
        account_id=account.id if account else None,
        vehicle_id=vehicle.id if vehicle else detection.vehicle_id,
        toll_price_id=price.id if price else None,
        detection_id=detection.id,
        idempotency_key=idempotency_key,
        processed_at=processed_at,
        amount=price.amount if price else Decimal("0.00"),
        status=status,
        failure_reason=message,
        balance_after=account.balance if account else None,
    )
    database.add(transaction)
    database.flush()
    if account is not None and vehicle is not None:
        _add_notification(
            database, vehicle.user_id, transaction, "payment_attention",
            f"Simulated toll payment needs attention: {message}",
        )
    database.commit()
    database.refresh(transaction)
    return PaymentOutcome(
        status, message, transaction.amount, transaction.balance_after, str(transaction.id)
    )


def _add_wallet_entry(
    database: Session, account: Account, transaction: TollTransaction | None,
    entry_type: str, amount: Decimal, direction: str, description: str, idempotency_key: str,
) -> WalletLedgerEntry:
    entry = WalletLedgerEntry(
        account_id=account.id, transaction_id=transaction.id if transaction else None,
        entry_type=entry_type, amount=amount, direction=direction,
        balance_after=account.balance, description=description, idempotency_key=idempotency_key,
    )
    database.add(entry)
    return entry


def _add_notification(
    database: Session, user_id, transaction: TollTransaction | None,
    notification_type: str, message: str,
) -> PaymentNotification:
    notification = PaymentNotification(
        user_id=user_id, transaction_id=transaction.id if transaction else None,
        notification_type=notification_type, message=message,
    )
    database.add(notification)
    return notification

"""Atomic simulated toll-payment workflow for recognized number plates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from alpr.plate.origin import OriginDecision, classify_plate_origin
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    DetectionRecord,
    ForeignVehicleChargeSettings,
    PaymentNotification,
    TollPrice,
    TollTransaction,
    Vehicle,
    WalletLedgerEntry,
)
from app.services.detection.gemini_fallback import ValidatedFallback, revalidate_evidence
from app.services.locations import default_toll_location_id


@dataclass(frozen=True)
class PaymentOutcome:
    status: str
    message: str
    amount: Decimal
    balance_after: Decimal | None
    transaction_id: str | None
    duplicate: bool = False
    dynamic_toll_amount: Decimal = Decimal("0.00")
    foreign_vehicle_charge: Decimal = Decimal("0.00")


def recognition_is_charge_eligible(
    recognition_accepted: bool, normalized_plate: str | None
) -> bool:
    """Return whether a recognition can enter the simulated payment workflow."""
    return recognition_accepted and bool(normalized_plate) and classify_plate_origin(normalized_plate).origin != "unknown"


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
    origin_reason: str | None = None,
    fallback_evidence: ValidatedFallback | None = None,
    recognition_source: str = "local_alpr",
    origin_source: str = "local_rules",
    fallback_used: bool = False,
    fallback_status: str = "not_requested",
    source: str = "webcam",
    detected_at: datetime | None = None,
    location_id: UUID | None = None,
    prepared_price_id: UUID | None = None,
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
            dynamic_toll_amount=existing.dynamic_toll_amount,
            foreign_vehicle_charge=existing.foreign_vehicle_charge,
        )

    now = detected_at or datetime.now(UTC)
    location_id = location_id or default_toll_location_id(database)
    origin = (
        classify_plate_origin(normalized_plate)
        if recognition_accepted
        else OriginDecision("unknown", origin_reason or "not_evaluated_or_rejected")
    )
    eligible = recognition_is_charge_eligible(recognition_accepted, normalized_plate)
    country = {"malaysian": "Malaysia", "singaporean": "Singapore"}.get(origin.origin)
    if fallback_evidence is not None:
        eligible = recognition_accepted and revalidate_evidence(fallback_evidence, normalized_plate)
        origin = OriginDecision(fallback_evidence.origin, "gemini_validated_pattern") if eligible else OriginDecision("unknown", "invalid_fallback_evidence")
        country = fallback_evidence.country if eligible else None
    detection = DetectionRecord(
        location_id=location_id,
        detected_at=now,
        raw_plate_text=raw_plate_text,
        normalized_plate=normalized_plate,
        plate_origin=origin.origin,
        origin_reason=origin.reason,
        detection_confidence=Decimal(str(detection_confidence)) if detection_confidence is not None else None,
        ocr_confidence=Decimal(str(ocr_confidence)) if ocr_confidence is not None else None,
        status="accepted" if eligible else "low_confidence",
        review_status="not_required" if eligible else "pending",
        source=source,
        recognition_source=recognition_source,
        origin_source=origin_source,
        origin_country=country,
        fallback_used=fallback_used,
        fallback_provider="gemini" if fallback_used else None,
        fallback_status=fallback_status,
    )
    database.add(detection)
    database.flush()

    price = database.scalar(
        select(TollPrice)
        .where(TollPrice.location_id == location_id, TollPrice.effective_at <= now,
               TollPrice.id == prepared_price_id if prepared_price_id is not None else True)
        .order_by(TollPrice.effective_at.desc(), TollPrice.created_at.desc(), TollPrice.id.desc())
        .limit(1)
    )
    if not eligible:
        reason = (
            "Plate origin is ambiguous or unsupported; no simulated deduction was made."
            if recognition_accepted and normalized_plate and origin.origin == "unknown"
            else "Recognition did not pass confidence checks."
        )
        return _record_failure(
            database,
            detection,
            idempotency_key,
            now,
            "low_confidence",
            reason,
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

    foreign_charge = Decimal("0.00")
    if origin.origin in {"singaporean", "foreign_other"}:
        charge_settings = database.get(ForeignVehicleChargeSettings, "default")
        if charge_settings is None:
            detection.status = "error"
            return _record_failure(
                database, detection, idempotency_key, now, "failed",
                "Simulated foreign-vehicle charge is not configured; no deduction was made.",
                price=price,
            )
        foreign_charge = charge_settings.amount
    final_total = price.amount + foreign_charge

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
            foreign_charge=foreign_charge,
        )

    if vehicle.registration_origin != origin.origin or (
        origin.origin == "foreign_other" and vehicle.origin_country != country
    ) or (
        vehicle.origin_country is not None and vehicle.origin_country != country
    ):
        detection.status = "error"
        return _record_failure(
            database, detection, idempotency_key, now, "failed",
            "Recognized plate origin does not match the registered simulated vehicle.",
            vehicle=vehicle, price=price, foreign_charge=foreign_charge,
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
            foreign_charge=foreign_charge,
        )
    if not has_sufficient_balance(account.balance, final_total):
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
            foreign_charge=foreign_charge,
        )

    account.balance = balance_after_toll(account.balance, final_total)
    transaction = TollTransaction(
        location_id=location_id,
        account_id=account.id,
        vehicle_id=vehicle.id,
        toll_price_id=price.id,
        detection_id=detection.id,
        idempotency_key=idempotency_key,
        processed_at=now,
        amount=final_total,
        dynamic_toll_amount=price.amount,
        foreign_vehicle_charge=foreign_charge,
        status="successful",
        balance_after=account.balance,
    )
    database.add(transaction)
    database.flush()
    _add_wallet_entry(
        database, account, transaction, "toll_deduction", final_total, "debit",
        f"Simulated toll deduction at {location_id}.", f"toll:{idempotency_key}",
    )
    notification_message = f"Simulated toll payment of RM{final_total:.2f} was processed."
    if foreign_charge:
        notification_message = (
            f"Simulated toll payment of RM{final_total:.2f} was processed "
            f"(RM{price.amount:.2f} dynamic toll + RM{foreign_charge:.2f} simulated foreign-vehicle charge)."
        )
    _add_notification(
        database, vehicle.user_id, transaction, "payment_success",
        notification_message,
    )
    database.commit()
    database.refresh(transaction)
    return PaymentOutcome(
        "successful",
        "Simulated toll payment was processed.",
        transaction.amount,
        transaction.balance_after,
        str(transaction.id),
        dynamic_toll_amount=transaction.dynamic_toll_amount,
        foreign_vehicle_charge=transaction.foreign_vehicle_charge,
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
    foreign_charge: Decimal = Decimal("0.00"),
) -> PaymentOutcome:
    dynamic_toll_amount = price.amount if price else Decimal("0.00")
    attempted_total = dynamic_toll_amount + foreign_charge
    transaction = TollTransaction(
        location_id=detection.location_id,
        account_id=account.id if account else None,
        vehicle_id=vehicle.id if vehicle else detection.vehicle_id,
        toll_price_id=price.id if price else None,
        detection_id=detection.id,
        idempotency_key=idempotency_key,
        processed_at=processed_at,
        amount=attempted_total,
        dynamic_toll_amount=dynamic_toll_amount,
        foreign_vehicle_charge=foreign_charge,
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
        status, message, transaction.amount, transaction.balance_after, str(transaction.id),
        dynamic_toll_amount=transaction.dynamic_toll_amount,
        foreign_vehicle_charge=transaction.foreign_vehicle_charge,
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

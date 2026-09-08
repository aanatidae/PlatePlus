"""Validated persistence endpoints for synthetic prototype data."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from typing import Annotated, TypeVar
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.db.session import get_db
from app.models import (
    Account,
    Admin,
    DetectionRecord,
    PaymentNotification,
    TollLocation,
    TollPrice,
    TollTransaction,
    TrafficRecord,
    User,
    Vehicle,
    WalletLedgerEntry,
)
from app.schemas.database import (
    AccountCreate,
    AccountRead,
    AdminRead,
    DetectionRecordCreate,
    DetectionRecordRead,
    DetectionReviewUpdate,
    PaymentNotificationRead,
    TollPriceCreate,
    TollPriceRead,
    TollTransactionCreate,
    TollTransactionRead,
    TrafficRecordCreate,
    TrafficRecordRead,
    TransactionReversalCreate,
    UserCreate,
    UserRead,
    VehicleCreate,
    VehicleRead,
    WalletLedgerEntryRead,
    WalletTopUpCreate,
)

router = APIRouter(
    prefix="/api/data", tags=["database"], dependencies=[Depends(require_admin)]
)
ModelT = TypeVar("ModelT")
DatabaseSession = Annotated[Session, Depends(get_db)]


def _save(database: Session, entity: ModelT, conflict_message: str) -> ModelT:
    try:
        database.add(entity)
        database.commit()
        database.refresh(entity)
        return entity
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=conflict_message
        ) from error


def _require(database: Session, model: type[ModelT], entity_id: UUID, label: str) -> ModelT:
    entity = database.get(model, entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} was not found.")
    return entity


def _list(database: Session, model: type[ModelT], offset: int, limit: int) -> list[ModelT]:
    return list(database.scalars(select(model).offset(offset).limit(limit)))


def _location(database: Session, location_id: UUID | None) -> UUID | None:
    if location_id is not None and database.get(TollLocation, location_id) is None:
        raise HTTPException(status_code=404, detail="Toll location was not found.")
    return location_id


def history_options(
    start_at: datetime | None = None, end_at: datetime | None = None,
    congestion_category: str | None = None, plate: str | None = None,
    detection_status: str | None = None, registration: str | None = None,
    transaction_status: str | None = None,
    minimum_amount: Annotated[Decimal | None, Query(ge=0)] = None,
) -> dict:
    start = start_at.replace(tzinfo=UTC) if start_at and start_at.tzinfo is None else start_at
    end = end_at.replace(tzinfo=UTC) if end_at and end_at.tzinfo is None else end_at
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="Start date must be before end date.")
    return {
        "start": start, "end": end, "congestion_category": congestion_category, "plate": plate,
        "detection_status": detection_status, "registration": registration,
        "transaction_status": transaction_status, "minimum_amount": minimum_amount,
    }


def filtered_history(database, model, timestamp, location_id, options, offset, limit):
    _location(database, location_id)
    statement = select(model)
    if location_id:
        statement = statement.where(model.location_id == location_id)
    if options["start"]:
        statement = statement.where(timestamp >= options["start"])
    if options["end"]:
        statement = statement.where(timestamp <= options["end"])
    if model is TollPrice and options["congestion_category"]:
        aliases = {"low": ["low", "normal"], "high": ["high", "peak_hour"]}
        category = options["congestion_category"]
        statement = statement.where(model.congestion_category.in_(aliases.get(category, [category])))
    if model is DetectionRecord:
        if options["plate"]:
            statement = statement.where(model.normalized_plate.contains(options["plate"].upper(), autoescape=True))
        if options["detection_status"]:
            statement = statement.where(model.status == options["detection_status"])
        if options["registration"]:
            statement = statement.where(model.vehicle_id.is_not(None) if options["registration"] == "registered" else model.vehicle_id.is_(None))
    if model is TollTransaction:
        if options["transaction_status"]:
            statement = statement.where(model.status == options["transaction_status"])
        if options["minimum_amount"] is not None:
            statement = statement.where(model.amount >= options["minimum_amount"])
    return list(database.scalars(statement.order_by(timestamp.desc(), model.id).offset(offset).limit(limit)))


def _history_rows(database: Session, model, timestamp, location_id: UUID | None, options: dict):
    """Return the bounded operational history used by dashboard analysis and CSV export."""
    return filtered_history(database, model, timestamp, location_id, options, 0, 1000)


def _malaysia_day(value: datetime) -> str:
    return value.astimezone(ZoneInfo("Asia/Kuala_Lumpur")).date().isoformat()


def _history_analytics(database: Session, location_id: UUID | None, options: dict) -> dict:
    prices = _history_rows(database, TollPrice, TollPrice.effective_at, location_id, options)
    detections = _history_rows(database, DetectionRecord, DetectionRecord.detected_at, location_id, options)
    transactions = _history_rows(database, TollTransaction, TollTransaction.processed_at, location_id, options)
    traffic = _history_rows(database, TrafficRecord, TrafficRecord.measured_at, location_id, options)
    if options["congestion_category"]:
        aliases = {"low": {"low", "normal"}, "high": {"high", "peak_hour"}}
        expected = aliases.get(options["congestion_category"], {options["congestion_category"]})
        traffic = [item for item in traffic if item.congestion_category in expected]

    names = {item.id: item.display_name for item in database.scalars(select(TollLocation))}
    pricing_by_day: dict[str, list[Decimal]] = defaultdict(list)
    congestion_by_day: dict[str, list[Decimal]] = defaultdict(list)
    revenue_by_day: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    successes_by_day: dict[str, int] = defaultdict(int)
    totals_by_day: dict[str, int] = defaultdict(int)
    low_confidence_by_day: dict[str, int] = defaultdict(int)
    detections_by_day: dict[str, int] = defaultdict(int)
    per_location: dict[UUID, dict[str, object]] = {}
    scenarios: dict[str, list[TrafficRecord]] = defaultdict(list)

    for item in prices:
        pricing_by_day[_malaysia_day(item.effective_at)].append(item.amount)
        row = per_location.setdefault(item.location_id, {"prices": [], "traffic": []})
        row["prices"].append(item.amount)
    for item in traffic:
        congestion_by_day[_malaysia_day(item.measured_at)].append(item.congestion_percentage)
        scenarios[item.scenario].append(item)
        row = per_location.setdefault(item.location_id, {"prices": [], "traffic": []})
        row["traffic"].append(item.congestion_percentage)
    for item in detections:
        day = _malaysia_day(item.detected_at)
        detections_by_day[day] += 1
        if item.status == "low_confidence":
            low_confidence_by_day[day] += 1
    for item in transactions:
        day = _malaysia_day(item.processed_at)
        totals_by_day[day] += 1
        if item.status == "successful":
            successes_by_day[day] += 1
            if item.reversed_at is None:
                revenue_by_day[day] += item.amount

    days = sorted(set(pricing_by_day) | set(congestion_by_day) | set(detections_by_day) | set(totals_by_day))
    series = [{
        "date": day,
        "average_toll": sum(pricing_by_day[day], Decimal("0")) / len(pricing_by_day[day]) if pricing_by_day[day] else None,
        "average_congestion": sum(congestion_by_day[day], Decimal("0")) / len(congestion_by_day[day]) if congestion_by_day[day] else None,
        "detections": detections_by_day[day],
        "low_confidence": low_confidence_by_day[day],
        "transactions": totals_by_day[day],
        "payment_success_rate": (successes_by_day[day] / totals_by_day[day] * 100) if totals_by_day[day] else None,
        "simulated_revenue": revenue_by_day[day],
    } for day in days]
    locations = [{
        "location_id": str(identifier), "display_name": names.get(identifier, "Unknown location"),
        "average_toll": sum(values["prices"], Decimal("0")) / len(values["prices"]) if values["prices"] else None,
        "average_congestion": sum(values["traffic"], Decimal("0")) / len(values["traffic"]) if values["traffic"] else None,
        "price_records": len(values["prices"]), "traffic_records": len(values["traffic"]),
    } for identifier, values in per_location.items()]
    scenario_comparison = [{
        "scenario": scenario,
        "records": len(records),
        "average_congestion": sum((item.congestion_percentage for item in records), Decimal("0")) / len(records),
        "average_speed_kmh": None,
    } for scenario, records in sorted(scenarios.items())]
    return {"scope": "location" if location_id else "all_locations", "series": series,
            "locations": locations, "scenario_comparison": scenario_comparison,
            "totals": {"price_records": len(prices), "traffic_records": len(traffic), "detections": len(detections), "transactions": len(transactions)}}


@router.get("/admins", response_model=list[AdminRead])
def list_admins(
    database: DatabaseSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    return _list(database, Admin, offset, limit)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, database: DatabaseSession):
    return _save(database, User(**payload.model_dump()), "A user with this email already exists.")


@router.get("/users", response_model=list[UserRead])
def list_users(
    database: DatabaseSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    return _list(database, User, offset, limit)


@router.post("/accounts", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, database: DatabaseSession):
    _require(database, User, payload.user_id, "User")
    account = Account(**payload.model_dump(), opening_balance=payload.balance)
    try:
        database.add(account)
        database.flush()
        database.add(WalletLedgerEntry(
            account_id=account.id, entry_type="opening_balance", amount=payload.balance,
            direction="credit", balance_after=payload.balance,
            description="Opening simulated wallet balance.", idempotency_key=f"opening:{account.id}",
        ))
        database.commit()
        database.refresh(account)
        return account
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(status_code=409, detail="The account could not be created.") from error


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    database: DatabaseSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    return _list(database, Account, offset, limit)


@router.get("/accounts/{account_id}/ledger", response_model=list[WalletLedgerEntryRead])
def account_ledger(
    account_id: UUID, database: DatabaseSession,
    limit: int = Query(50, ge=1, le=200),
):
    _require(database, Account, account_id, "Account")
    return list(database.scalars(
        select(WalletLedgerEntry).where(WalletLedgerEntry.account_id == account_id)
        .order_by(WalletLedgerEntry.created_at.desc()).limit(limit)
    ))


@router.post("/accounts/{account_id}/top-ups", response_model=AccountRead)
def top_up_account(account_id: UUID, payload: WalletTopUpCreate, database: DatabaseSession):
    account = _require(database, Account, account_id, "Account")
    existing = database.scalar(select(WalletLedgerEntry).where(
        WalletLedgerEntry.idempotency_key == payload.idempotency_key
    ))
    if existing is not None:
        if existing.account_id != account.id:
            raise HTTPException(status_code=409, detail="The top-up idempotency key was already used.")
        return account
    account.balance += payload.amount
    database.add(WalletLedgerEntry(
        account_id=account.id, entry_type="top_up", amount=payload.amount, direction="credit",
        balance_after=account.balance, description=payload.note or "Simulated wallet top-up.",
        idempotency_key=payload.idempotency_key,
    ))
    database.add(PaymentNotification(
        user_id=account.user_id, notification_type="top_up",
        message=f"Simulated wallet top-up of RM{payload.amount:.2f} was added.",
    ))
    database.commit()
    database.refresh(account)
    return account


@router.post("/vehicles", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreate, database: DatabaseSession):
    _require(database, User, payload.user_id, "User")
    return _save(
        database, Vehicle(**payload.model_dump()), "A vehicle with this plate already exists."
    )


@router.get("/vehicles", response_model=list[VehicleRead])
def list_vehicles(
    database: DatabaseSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    return _list(database, Vehicle, offset, limit)


@router.post(
    "/traffic-records", response_model=TrafficRecordRead, status_code=status.HTTP_201_CREATED
)
def create_traffic_record(payload: TrafficRecordCreate, database: DatabaseSession):
    return _save(
        database, TrafficRecord(**payload.model_dump()), "The traffic record could not be created."
    )


@router.get("/traffic-records", response_model=list[TrafficRecordRead])
def list_traffic_records(
    database: DatabaseSession, location_id: UUID | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    location_id = _location(database, location_id)
    statement = (
        select(TrafficRecord).where(TrafficRecord.location_id == location_id).order_by(TrafficRecord.measured_at.desc()).offset(offset).limit(limit)
        if location_id else select(TrafficRecord).order_by(TrafficRecord.measured_at.desc()).offset(offset).limit(limit)
    )
    return list(database.scalars(statement))


@router.post("/toll-prices", response_model=TollPriceRead, status_code=status.HTTP_201_CREATED)
def create_toll_price(payload: TollPriceCreate, database: DatabaseSession):
    if payload.traffic_record_id:
        _require(database, TrafficRecord, payload.traffic_record_id, "Traffic record")
    return _save(
        database, TollPrice(**payload.model_dump()), "The toll price could not be created."
    )


@router.get("/toll-prices", response_model=list[TollPriceRead])
def list_toll_prices(
    database: DatabaseSession, options: Annotated[dict, Depends(history_options)],
    location_id: UUID | None = None,
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
):
    return filtered_history(database, TollPrice, TollPrice.effective_at, location_id, options, offset, limit)


@router.post("/detections", response_model=DetectionRecordRead, status_code=status.HTTP_201_CREATED)
def create_detection(payload: DetectionRecordCreate, database: DatabaseSession):
    if payload.vehicle_id:
        _require(database, Vehicle, payload.vehicle_id, "Vehicle")
    return _save(
        database,
        DetectionRecord(**payload.model_dump()),
        "The detection record could not be created.",
    )


@router.get("/detections", response_model=list[DetectionRecordRead])
def list_detections(
    database: DatabaseSession, options: Annotated[dict, Depends(history_options)],
    location_id: UUID | None = None,
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
):
    return filtered_history(database, DetectionRecord, DetectionRecord.detected_at, location_id, options, offset, limit)


@router.patch("/detections/{detection_id}/review", response_model=DetectionRecordRead)
def review_detection(detection_id: UUID, payload: DetectionReviewUpdate, database: DatabaseSession):
    detection = _require(database, DetectionRecord, detection_id, "Detection record")
    if detection.review_status != "pending":
        raise HTTPException(status_code=409, detail="This recognition does not require manual review.")
    detection.review_status = payload.review_status
    detection.review_note = payload.review_note
    detection.reviewed_at = datetime.now(UTC)
    database.commit()
    database.refresh(detection)
    return detection


@router.post(
    "/transactions", response_model=TollTransactionRead, status_code=status.HTTP_201_CREATED
)
def create_transaction(payload: TollTransactionCreate, database: DatabaseSession):
    for entity_id, model, label in (
        (payload.account_id, Account, "Account"),
        (payload.vehicle_id, Vehicle, "Vehicle"),
        (payload.toll_price_id, TollPrice, "Toll price"),
        (payload.detection_id, DetectionRecord, "Detection record"),
    ):
        if entity_id:
            _require(database, model, entity_id, label)
    return _save(
        database,
        TollTransaction(**payload.model_dump()),
        "The idempotency key or detection was already used.",
    )


@router.get("/transactions", response_model=list[TollTransactionRead])
def list_transactions(
    database: DatabaseSession, options: Annotated[dict, Depends(history_options)],
    location_id: UUID | None = None,
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
):
    return filtered_history(database, TollTransaction, TollTransaction.processed_at, location_id, options, offset, limit)


@router.post("/transactions/{transaction_id}/reversal", response_model=TollTransactionRead)
def reverse_transaction(
    transaction_id: UUID, payload: TransactionReversalCreate, database: DatabaseSession,
):
    transaction = _require(database, TollTransaction, transaction_id, "Toll transaction")
    if transaction.status != "successful" or transaction.account_id is None:
        raise HTTPException(status_code=422, detail="Only successful simulated payments can be reversed.")
    if transaction.reversed_at is not None:
        return transaction
    existing = database.scalar(select(WalletLedgerEntry).where(
        WalletLedgerEntry.idempotency_key == payload.idempotency_key
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="The reversal idempotency key was already used.")
    account = database.scalar(select(Account).where(Account.id == transaction.account_id).with_for_update())
    if account is None:
        raise HTTPException(status_code=409, detail="The simulated account is no longer available.")
    account.balance += transaction.amount
    now = datetime.now(UTC)
    transaction.reversed_at = now
    transaction.reversal_reason = payload.reason
    database.add(WalletLedgerEntry(
        account_id=account.id, transaction_id=transaction.id, entry_type="reversal", amount=transaction.amount,
        direction="credit", balance_after=account.balance, description=f"Simulated reversal: {payload.reason}",
        idempotency_key=payload.idempotency_key,
    ))
    database.add(PaymentNotification(
        user_id=account.user_id, transaction_id=transaction.id, notification_type="reversal",
        message=f"Simulated reversal of RM{transaction.amount:.2f} was issued.",
    ))
    database.commit()
    database.refresh(transaction)
    return transaction


@router.get("/payment-summary")
def payment_summary(database: DatabaseSession, location_id: UUID | None = None):
    location_id = _location(database, location_id)
    statement = select(TollTransaction)
    if location_id:
        statement = statement.where(TollTransaction.location_id == location_id)
    transactions = list(database.scalars(statement))
    successful = [item for item in transactions if item.status == "successful"]
    reversed_amount = sum((item.amount for item in successful if item.reversed_at is not None), Decimal("0.00"))
    return {
        "scope": "location" if location_id else "all_locations",
        "location_id": location_id,
        "transaction_count": len(transactions),
        "successful_count": len(successful),
        "successful_revenue": sum((item.amount for item in successful), Decimal("0.00")),
        "reversed_amount": reversed_amount,
        "net_revenue": sum((item.amount for item in successful), Decimal("0.00")) - reversed_amount,
        "by_location": [
            {"location_id": item.id, "display_name": item.display_name,
             "transactions": sum(1 for row in transactions if row.location_id == item.id),
             "revenue": sum((row.amount for row in successful if row.location_id == item.id and row.reversed_at is None), Decimal("0.00"))}
            for item in database.scalars(select(TollLocation).order_by(TollLocation.display_name))
            if location_id is None or item.id == location_id
        ],
    }


@router.get("/payment-notifications", response_model=list[PaymentNotificationRead])
def payment_notifications(database: DatabaseSession, limit: int = Query(20, ge=1, le=100)):
    return list(database.scalars(
        select(PaymentNotification).order_by(PaymentNotification.created_at.desc()).limit(limit)
    ))


@router.get("/history/analytics")
def history_analytics(
    database: DatabaseSession, options: Annotated[dict, Depends(history_options)],
    location_id: UUID | None = None,
):
    """Location-aware historical aggregates for existing operational pages."""
    _location(database, location_id)
    return _history_analytics(database, location_id, options)


@router.get("/history/export.csv")
def history_export_csv(
    database: DatabaseSession, options: Annotated[dict, Depends(history_options)],
    location_id: UUID | None = None,
):
    """Export the currently scoped simulated operational history without a new analytics page."""
    _location(database, location_id)
    analytics = _history_analytics(database, location_id, options)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "average_toll_myr", "average_congestion_percentage", "detections", "low_confidence", "transactions", "payment_success_rate_percentage", "simulated_revenue_myr"])
    for item in analytics["series"]:
        writer.writerow([item["date"], item["average_toll"], item["average_congestion"], item["detections"], item["low_confidence"], item["transactions"], item["payment_success_rate"], item["simulated_revenue"]])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=plateplus-simulated-history.csv"})

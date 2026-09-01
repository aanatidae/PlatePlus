"""Validated persistence endpoints for synthetic prototype data."""

from __future__ import annotations

from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.db.session import get_db
from app.models import (
    Account,
    Admin,
    DetectionRecord,
    TollPrice,
    TollTransaction,
    TrafficRecord,
    User,
    Vehicle,
)
from app.schemas.database import (
    AccountCreate,
    AccountRead,
    AdminRead,
    DetectionRecordCreate,
    DetectionRecordRead,
    TollPriceCreate,
    TollPriceRead,
    TollTransactionCreate,
    TollTransactionRead,
    TrafficRecordCreate,
    TrafficRecordRead,
    UserCreate,
    UserRead,
    VehicleCreate,
    VehicleRead,
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
    return _save(database, Account(**payload.model_dump()), "The account could not be created.")


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    database: DatabaseSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    return _list(database, Account, offset, limit)


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
    database: DatabaseSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    statement = (
        select(TrafficRecord).order_by(TrafficRecord.measured_at.desc()).offset(offset).limit(limit)
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
    database: DatabaseSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    statement = (
        select(TollPrice).order_by(TollPrice.effective_at.desc()).offset(offset).limit(limit)
    )
    return list(database.scalars(statement))


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
    database: DatabaseSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    statement = (
        select(DetectionRecord)
        .order_by(DetectionRecord.detected_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(database.scalars(statement))


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
    database: DatabaseSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    statement = (
        select(TollTransaction)
        .order_by(TollTransaction.processed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(database.scalars(statement))

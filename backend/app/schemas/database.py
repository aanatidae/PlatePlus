"""Validated API schemas for database-backed prototype resources."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32)


class UserRead(ORMModel):
    id: UUID
    full_name: str
    email: str
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccountCreate(BaseModel):
    user_id: UUID
    balance: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    currency: Literal["MYR"] = "MYR"
    is_primary: bool = False


class AccountRead(ORMModel):
    id: UUID
    user_id: UUID
    balance: Decimal
    opening_balance: Decimal
    currency: str
    is_active: bool
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class VehicleCreate(BaseModel):
    user_id: UUID
    plate_number: str = Field(min_length=2, max_length=16)
    registration_origin: Literal["malaysian", "singaporean", "foreign_other"] = "malaysian"
    origin_country: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def require_other_country(self):
        if self.registration_origin == "foreign_other" and self.origin_country != "United Kingdom":
            raise ValueError("Other-foreign registrations currently require United Kingdom country.")
        expected = {"malaysian": "Malaysia", "singaporean": "Singapore"}.get(self.registration_origin)
        if expected and self.origin_country and self.origin_country != expected:
            raise ValueError("Country must agree with the declared synthetic registration origin.")
        return self
    make: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=40)

    @field_validator("plate_number")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        normalized = re.sub(r"[^A-Z0-9]", "", value.upper())
        if len(normalized) < 2:
            raise ValueError("plate_number must contain at least two letters or digits")
        return normalized


class VehicleRead(ORMModel):
    id: UUID
    user_id: UUID
    plate_number: str
    registration_origin: str
    origin_country: str | None
    make: str | None
    model: str | None
    color: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminRead(ORMModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TrafficRecordCreate(BaseModel):
    measured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    vehicle_count: int = Field(ge=0)
    road_capacity: int = Field(gt=0)
    congestion_percentage: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    congestion_category: Literal["low", "moderate", "high", "severe"]
    scenario: Literal["normal", "moderate", "peak_hour", "severe"] = "normal"


class TrafficRecordRead(ORMModel):
    id: UUID
    location_id: UUID
    measured_at: datetime
    vehicle_count: int
    road_capacity: int
    congestion_percentage: Decimal
    congestion_category: str
    scenario: str
    is_simulated: bool
    created_at: datetime


class TollPriceCreate(BaseModel):
    traffic_record_id: UUID | None = None
    effective_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    amount: Decimal = Field(ge=0, max_digits=8, decimal_places=2)
    currency: Literal["MYR"] = "MYR"
    congestion_category: Literal["low", "moderate", "high", "severe"]
    rule_version: str = Field(default="v1", min_length=1, max_length=32)


class TollPriceRead(ORMModel):
    id: UUID
    traffic_record_id: UUID | None
    location_id: UUID
    effective_at: datetime
    amount: Decimal
    currency: str
    congestion_category: str
    rule_version: str
    is_simulated: bool
    created_at: datetime


class DetectionRecordCreate(BaseModel):
    vehicle_id: UUID | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw_plate_text: str | None = Field(default=None, max_length=64)
    normalized_plate: str | None = Field(default=None, max_length=16)
    plate_origin: Literal["malaysian", "singaporean", "unknown"] = "unknown"
    origin_reason: str | None = Field(default=None, max_length=64)
    detection_confidence: Decimal = Field(ge=0, le=1, max_digits=5, decimal_places=4)
    ocr_confidence: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)
    status: Literal["accepted", "low_confidence", "unknown_vehicle", "duplicate", "error"]
    source: Literal["webcam", "upload", "test"] = "webcam"

    @field_validator("normalized_plate")
    @classmethod
    def normalize_optional_plate(cls, value: str | None) -> str | None:
        return re.sub(r"[^A-Z0-9]", "", value.upper()) if value else None


class DetectionRecordRead(ORMModel):
    id: UUID
    vehicle_id: UUID | None
    location_id: UUID
    detected_at: datetime
    raw_plate_text: str | None
    normalized_plate: str | None
    plate_origin: str
    origin_reason: str | None
    detection_confidence: Decimal | None
    ocr_confidence: Decimal | None
    recognition_source: str
    origin_source: str
    origin_country: str | None
    fallback_used: bool
    fallback_provider: str | None
    fallback_status: str
    status: str
    source: str
    image_path: str | None
    crop_path: str | None
    review_status: str
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class TollTransactionCreate(BaseModel):
    account_id: UUID | None = None
    vehicle_id: UUID | None = None
    toll_price_id: UUID | None = None
    detection_id: UUID | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    amount: Decimal = Field(ge=0, max_digits=8, decimal_places=2)
    dynamic_toll_amount: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    foreign_vehicle_charge: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=8, decimal_places=2)
    currency: Literal["MYR"] = "MYR"
    status: Literal[
        "successful",
        "insufficient_balance",
        "unknown_vehicle",
        "low_confidence",
        "duplicate",
        "failed",
    ]
    failure_reason: str | None = Field(default=None, max_length=255)
    balance_after: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def reconcile_components(self) -> TollTransactionCreate:
        if self.dynamic_toll_amount is None:
            self.dynamic_toll_amount = self.amount - self.foreign_vehicle_charge
        if self.dynamic_toll_amount < 0 or self.amount != self.dynamic_toll_amount + self.foreign_vehicle_charge:
            raise ValueError("amount must equal dynamic_toll_amount plus foreign_vehicle_charge")
        return self


class TollTransactionRead(ORMModel):
    id: UUID
    account_id: UUID | None
    location_id: UUID
    vehicle_id: UUID | None
    toll_price_id: UUID | None
    detection_id: UUID | None
    idempotency_key: str
    processed_at: datetime
    amount: Decimal
    dynamic_toll_amount: Decimal
    foreign_vehicle_charge: Decimal
    currency: str
    status: str
    failure_reason: str | None
    balance_after: Decimal | None
    is_simulated: bool
    created_at: datetime
    reversed_at: datetime | None
    reversal_reason: str | None


class ForeignVehicleChargeUpdate(BaseModel):
    amount: Decimal = Field(ge=0, max_digits=8, decimal_places=2)


class ForeignVehicleChargeRead(ORMModel):
    amount: Decimal
    updated_at: datetime


class WalletTopUpCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    idempotency_key: str = Field(min_length=8, max_length=128)
    note: str | None = Field(default=None, max_length=160)


class WalletLedgerEntryRead(ORMModel):
    id: UUID
    account_id: UUID
    transaction_id: UUID | None
    entry_type: str
    amount: Decimal
    direction: str
    balance_after: Decimal
    currency: str
    description: str
    created_at: datetime


class TransactionReversalCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=255)
    idempotency_key: str = Field(min_length=8, max_length=128)


class DetectionReviewUpdate(BaseModel):
    review_status: Literal["resolved", "dismissed"]
    review_note: str | None = Field(default=None, max_length=255)


class PaymentNotificationRead(ORMModel):
    id: UUID
    user_id: UUID
    transaction_id: UUID | None
    notification_type: str
    message: str
    read_at: datetime | None
    created_at: datetime

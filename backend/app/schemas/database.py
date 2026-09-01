"""Validated API schemas for database-backed prototype resources."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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


class AccountRead(ORMModel):
    id: UUID
    user_id: UUID
    balance: Decimal
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class VehicleCreate(BaseModel):
    user_id: UUID
    plate_number: str = Field(min_length=2, max_length=16)
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
    detected_at: datetime
    raw_plate_text: str | None
    normalized_plate: str | None
    detection_confidence: Decimal
    ocr_confidence: Decimal | None
    status: str
    source: str
    image_path: str | None
    crop_path: str | None
    created_at: datetime


class TollTransactionCreate(BaseModel):
    account_id: UUID | None = None
    vehicle_id: UUID | None = None
    toll_price_id: UUID | None = None
    detection_id: UUID | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    amount: Decimal = Field(ge=0, max_digits=8, decimal_places=2)
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


class TollTransactionRead(ORMModel):
    id: UUID
    account_id: UUID | None
    vehicle_id: UUID | None
    toll_price_id: UUID | None
    detection_id: UUID | None
    idempotency_key: str
    processed_at: datetime
    amount: Decimal
    currency: str
    status: str
    failure_reason: str | None
    balance_after: Decimal | None
    is_simulated: bool
    created_at: datetime

"""Database entities for the simulated toll-management prototype."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)


class Admin(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admins"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    accounts: Mapped[list[Account]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    vehicles: Mapped[list[Vehicle]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Account(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_accounts_balance_nonnegative"),
        CheckConstraint("currency = 'MYR'", name="ck_accounts_currency_myr"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="MYR", server_default="MYR"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped[User] = relationship(back_populates="accounts")
    transactions: Mapped[list[TollTransaction]] = relationship(back_populates="account")


class Vehicle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plate_number: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    make: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(80))
    color: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    user: Mapped[User] = relationship(back_populates="vehicles")
    transactions: Mapped[list[TollTransaction]] = relationship(back_populates="vehicle")
    detections: Mapped[list[DetectionRecord]] = relationship(back_populates="vehicle")


class TrafficRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "traffic_records"
    __table_args__ = (
        CheckConstraint(
            "congestion_percentage >= 0 AND congestion_percentage <= 100",
            name="ck_traffic_percentage_range",
        ),
        CheckConstraint("vehicle_count >= 0", name="ck_traffic_vehicle_count_nonnegative"),
        CheckConstraint("road_capacity > 0", name="ck_traffic_road_capacity_positive"),
    )

    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    vehicle_count: Mapped[int] = mapped_column(nullable=False)
    road_capacity: Mapped[int] = mapped_column(nullable=False)
    congestion_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    congestion_category: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    scenario: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    simulation_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    simulation_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_simulated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    toll_prices: Mapped[list[TollPrice]] = relationship(back_populates="traffic_record")


class TollPrice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "toll_prices"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_toll_prices_amount_nonnegative"),
        CheckConstraint("currency = 'MYR'", name="ck_toll_prices_currency_myr"),
    )

    traffic_record_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("traffic_records.id", ondelete="SET NULL"), index=True
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="MYR", server_default="MYR"
    )
    congestion_category: Mapped[str] = mapped_column(String(16), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    is_simulated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    traffic_record: Mapped[TrafficRecord | None] = relationship(back_populates="toll_prices")
    transactions: Mapped[list[TollTransaction]] = relationship(back_populates="toll_price")


class TrafficSimulationSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The single persisted configuration used by the backend scheduler."""

    __tablename__ = "traffic_simulation_settings"
    __table_args__ = (
        CheckConstraint("interval_minutes IN (1, 5, 15)", name="ck_simulation_interval"),
        CheckConstraint(
            "simulation_mode IN ('time_patterned', 'fixed_scenario')",
            name="ck_simulation_mode",
        ),
        CheckConstraint(
            "fixed_scenario IN ('normal', 'moderate', 'peak_hour', 'severe')",
            name="ck_simulation_fixed_scenario",
        ),
        CheckConstraint("time_mode IN ('real', 'simulated')", name="ck_simulation_time_mode"),
    )

    singleton_key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, default="default")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    interval_minutes: Mapped[int] = mapped_column(nullable=False, default=5)
    simulation_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="time_patterned")
    fixed_scenario: Mapped[str] = mapped_column(String(32), nullable=False, default="moderate")
    time_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="real")
    simulated_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    simulated_time_anchor: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pricing_rule_version: Mapped[int] = mapped_column(nullable=False, default=1)


class DynamicPricingRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One administrator-editable, fixed scenario pricing band."""

    __tablename__ = "dynamic_pricing_rules"
    __table_args__ = (
        CheckConstraint("minimum_percentage >= 0", name="ck_pricing_rule_minimum"),
        CheckConstraint("maximum_percentage <= 100", name="ck_pricing_rule_maximum"),
        CheckConstraint("minimum_percentage <= maximum_percentage", name="ck_pricing_rule_order"),
        CheckConstraint("amount >= 0", name="ck_pricing_rule_amount"),
    )

    scenario: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    congestion_category: Mapped[str] = mapped_column(String(16), nullable=False)
    minimum_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    maximum_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)


class AdminAuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only record of administrator changes to traffic configuration."""

    __tablename__ = "admin_audit_logs"

    admin_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("admins.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class DetectionRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "detection_records"
    __table_args__ = (
        CheckConstraint(
            "detection_confidence >= 0 AND detection_confidence <= 1",
            name="ck_detection_confidence_range",
        ),
        CheckConstraint(
            "ocr_confidence IS NULL OR (ocr_confidence >= 0 AND ocr_confidence <= 1)",
            name="ck_ocr_confidence_range",
        ),
        Index("ix_detection_records_plate_detected_at", "normalized_plate", "detected_at"),
    )

    vehicle_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), index=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    raw_plate_text: Mapped[str | None] = mapped_column(String(64))
    normalized_plate: Mapped[str | None] = mapped_column(String(16), index=True)
    detection_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    ocr_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="webcam")
    image_path: Mapped[str | None] = mapped_column(Text)
    crop_path: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text)

    vehicle: Mapped[Vehicle | None] = relationship(back_populates="detections")
    transaction: Mapped[TollTransaction | None] = relationship(back_populates="detection")


class TollTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "toll_transactions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_transactions_amount_nonnegative"),
        CheckConstraint(
            "balance_after IS NULL OR balance_after >= 0",
            name="ck_transactions_balance_nonnegative",
        ),
        CheckConstraint("currency = 'MYR'", name="ck_transactions_currency_myr"),
    )

    account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), index=True
    )
    vehicle_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), index=True
    )
    toll_price_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("toll_prices.id", ondelete="SET NULL"), index=True
    )
    detection_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("detection_records.id", ondelete="SET NULL"), unique=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="MYR", server_default="MYR"
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_simulated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    account: Mapped[Account | None] = relationship(back_populates="transactions")
    vehicle: Mapped[Vehicle | None] = relationship(back_populates="transactions")
    toll_price: Mapped[TollPrice | None] = relationship(back_populates="transactions")
    detection: Mapped[DetectionRecord | None] = relationship(back_populates="transaction")

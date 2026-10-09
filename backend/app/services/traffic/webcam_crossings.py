"""Canonical ALPR-crossing telemetry and pricing for Simulator Toll Plaza."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    DetectionRecord,
    DynamicPricingRule,
    TollLocation,
    TollPrice,
    TrafficRecord,
    TrafficSimulationSettings,
)
from app.services.traffic.pricing import decide_price
from app.services.traffic.simulation import rule_for_congestion

SIMULATOR_TOLL_CODE = "SIMULATOR"
COUNTED_WEBCAM_STATUSES = ("accepted", "unknown_vehicle")
SIMULATOR_ALPR_SOURCES = ("webcam", "webcam_alpr", "uploaded_image")


def is_webcam_toll(location: TollLocation) -> bool:
    return location.code == SIMULATOR_TOLL_CODE


def active_crossing_congestion(database: Session, location: TollLocation, now: datetime) -> tuple[int, Decimal]:
    """Read the shared rolling crossing window without creating traffic or detections."""
    crossings = int(database.scalar(select(func.count(DetectionRecord.id)).where(
        DetectionRecord.location_id == location.id,
        DetectionRecord.source.in_(SIMULATOR_ALPR_SOURCES),
        DetectionRecord.status.in_(COUNTED_WEBCAM_STATUSES),
        DetectionRecord.detected_at > now - timedelta(seconds=60),
        DetectionRecord.detected_at <= now,
    )))
    congestion = min(Decimal("100.00"), Decimal(crossings) * Decimal(100) / location.road_capacity)
    return crossings, congestion


def webcam_crossing_state(
    database: Session, location: TollLocation, now: datetime | None = None
) -> dict:
    """Calculate the rolling 60-second state without inventing fallback traffic."""
    now = now or datetime.now(UTC)
    rules = {item.scenario: item for item in database.scalars(select(DynamicPricingRule))}
    if not {"normal", "moderate", "peak_hour", "severe"}.issubset(rules):
        return {"telemetry": None, "source": "unavailable"}
    # Serialize arrival/expiry decisions per plaza. The caller commits only a
    # changed read-side price; arrivals keep the lock until payment commits.
    database.scalar(select(TollLocation).where(TollLocation.id == location.id).with_for_update())
    crossings, congestion = active_crossing_congestion(database, location, now)
    settings = database.scalar(select(TrafficSimulationSettings).where(TrafficSimulationSettings.singleton_key == "default"))
    rule = rule_for_congestion(rules, congestion)
    decision = decide_price(database, settings, location, congestion, now, context="webcam_crossing_expiry") if settings else None
    multiplier = decision.rule.multiplier if decision else (rule.amount / rules["normal"].amount if rules["normal"].amount else Decimal("1.00"))
    selected = decision.rule if decision else rule
    amount = decision.amount if decision else (location.base_toll * multiplier).quantize(Decimal("0.01"))
    price, changed = _persist_transition(database, location, now, amount, selected.congestion_category)
    latest_crossing = database.scalar(
        select(DetectionRecord.detected_at)
        .where(
            DetectionRecord.location_id == location.id,
            DetectionRecord.source.in_(SIMULATOR_ALPR_SOURCES),
            DetectionRecord.status.in_(COUNTED_WEBCAM_STATUSES),
            DetectionRecord.detected_at <= now,
        )
        .order_by(DetectionRecord.detected_at.desc())
    )
    return {"source": "webcam_alpr", "price_changed": changed, "telemetry": {
        "measured_at": now,
        "vehicle_count": crossings,
        "vehicles_per_hour": crossings,
        "active_crossings": crossings,
        "crossing_window_seconds": 60,
        "road_capacity": location.road_capacity,
        "congestion_percentage": congestion,
        "congestion_category": decision.rule.congestion_category if decision else rule.congestion_category,
        "base_toll_price": location.base_toll,
        "congestion_multiplier": multiplier,
        "current_toll_price": price.amount,
        "average_speed_kmh": None,
        "plaza_status": location.status,
        "camera_status": "online" if location.status == "operational" else "offline",
        "system_status": "healthy" if location.status == "operational" else location.status,
        "last_crossing_at": latest_crossing,
    }}


def has_recent_simulator_plate(
    database: Session, location: TollLocation, plate: str, now: datetime, cooldown_seconds: float
) -> bool:
    """Share the local ALPR cooldown across webcam and uploaded-image inputs."""
    return database.scalar(
        select(DetectionRecord.id).where(
            DetectionRecord.location_id == location.id,
            DetectionRecord.source.in_(SIMULATOR_ALPR_SOURCES),
            DetectionRecord.normalized_plate == plate,
            DetectionRecord.status.in_(COUNTED_WEBCAM_STATUSES),
            DetectionRecord.detected_at > now - timedelta(seconds=cooldown_seconds),
            DetectionRecord.detected_at <= now,
        ).limit(1)
    ) is not None


def _persist_transition(database: Session, location: TollLocation, now: datetime,
                        amount: Decimal, category: str, traffic_id=None) -> tuple[TollPrice, bool]:
    previous = database.scalar(select(TollPrice).where(
        TollPrice.location_id == location.id, TollPrice.effective_at <= now,
    ).order_by(TollPrice.effective_at.desc(), TollPrice.created_at.desc(), TollPrice.id.desc()).limit(1))
    if previous is not None and previous.amount == amount and previous.congestion_category == category:
        return previous, False
    price = TollPrice(
        traffic_record_id=traffic_id, location_id=location.id, effective_at=now,
        amount=amount, congestion_category=category, rule_version="webcam-v3",
        # PostgreSQL now() is constant during a transaction. Explicit creation
        # time orders two transitions with identical event timestamps correctly.
        created_at=datetime.now(UTC),
    )
    database.add(price)
    database.flush()
    return price, True


def prepare_webcam_crossing_price(database: Session, location: TollLocation, now: datetime) -> TollPrice | None:
    """Persist a price for the incoming accepted crossing before its payment is processed."""
    database.scalar(select(TollLocation).where(TollLocation.id == location.id).with_for_update())
    count, _ = active_crossing_congestion(database, location, now)
    next_count = count + 1
    congestion = min(Decimal("100.00"), Decimal(next_count) * Decimal(100) / location.road_capacity)
    rules = {item.scenario: item for item in database.scalars(select(DynamicPricingRule))}
    if not {"normal", "moderate", "peak_hour", "severe"}.issubset(rules):
        return None
    rule = rule_for_congestion(rules, congestion)
    settings = database.scalar(select(TrafficSimulationSettings).where(TrafficSimulationSettings.singleton_key == "default"))
    decision = decide_price(database, settings, location, congestion, now, context="webcam_crossing") if settings else None
    traffic = TrafficRecord(
        location_id=location.id, measured_at=now, simulation_time=now, vehicle_count=next_count,
        road_capacity=location.road_capacity, congestion_percentage=congestion,
        congestion_category=rule.congestion_category, scenario=rule.scenario,
        source="webcam_alpr", simulation_mode="live_webcam",
    )
    database.add(traffic)
    database.flush()
    amount = decision.amount if decision else (location.base_toll * (rule.amount / rules["normal"].amount if rules["normal"].amount else Decimal("1.00"))).quantize(Decimal("0.01"))
    price, _ = _persist_transition(database, location, now, amount,
                                   (decision.rule if decision else rule).congestion_category, traffic.id)
    return price

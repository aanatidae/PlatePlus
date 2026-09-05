"""Live, local-webcam-derived telemetry for the Simulator Toll Plaza."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DetectionRecord, DynamicPricingRule, TollLocation, TollPrice, TrafficRecord

SIMULATOR_TOLL_CODE = "SIMULATOR"
COUNTED_WEBCAM_STATUSES = ("accepted", "unknown_vehicle")


def is_webcam_toll(location: TollLocation) -> bool:
    return location.code == SIMULATOR_TOLL_CODE


def _rule_for_congestion(rules: dict[str, DynamicPricingRule], congestion: Decimal) -> DynamicPricingRule:
    return next(
        rule for rule in rules.values()
        if rule.minimum_percentage <= congestion <= rule.maximum_percentage
    )


def webcam_crossing_state(
    database: Session, location: TollLocation, now: datetime | None = None
) -> dict:
    """Calculate the rolling one-hour state without inventing fallback traffic."""
    now = now or datetime.now(UTC)
    rules = {item.scenario: item for item in database.scalars(select(DynamicPricingRule))}
    if not {"normal", "moderate", "peak_hour", "severe"}.issubset(rules):
        return {"telemetry": None, "source": "unavailable"}
    crossings = database.scalar(
        select(func.count(DetectionRecord.id))
        .where(
            DetectionRecord.location_id == location.id,
            DetectionRecord.source == "webcam",
            DetectionRecord.status.in_(COUNTED_WEBCAM_STATUSES),
            DetectionRecord.detected_at >= now - timedelta(hours=1),
        )
    )
    crossings = int(crossings)
    congestion = min(Decimal("100.00"), (Decimal(crossings) * Decimal(100) / location.road_capacity))
    rule = _rule_for_congestion(rules, congestion)
    normal_amount = rules["normal"].amount
    multiplier = (rule.amount / normal_amount).quantize(Decimal("0.01")) if normal_amount else Decimal("1.00")
    latest_crossing = database.scalar(
        select(DetectionRecord.detected_at)
        .where(
            DetectionRecord.location_id == location.id,
            DetectionRecord.source == "webcam",
            DetectionRecord.status.in_(COUNTED_WEBCAM_STATUSES),
        )
        .order_by(DetectionRecord.detected_at.desc())
    )
    return {"source": "webcam_alpr", "telemetry": {
        "measured_at": latest_crossing or now,
        "vehicle_count": crossings,
        "vehicles_per_hour": crossings,
        "road_capacity": location.road_capacity,
        "congestion_percentage": congestion,
        "congestion_category": rule.congestion_category,
        "base_toll_price": location.base_toll,
        "congestion_multiplier": multiplier,
        "current_toll_price": (location.base_toll * multiplier).quantize(Decimal("0.01")),
        "average_speed_kmh": None,
        "plaza_status": location.status,
        "camera_status": "online" if location.status == "operational" else "offline",
        "system_status": "healthy" if location.status == "operational" else location.status,
        "last_crossing_at": latest_crossing,
    }}


def prepare_webcam_crossing_price(database: Session, location: TollLocation, now: datetime) -> None:
    """Persist a price for the incoming accepted crossing before its payment is processed."""
    state = webcam_crossing_state(database, location, now)["telemetry"]
    if state is None:
        return
    next_count = state["vehicle_count"] + 1
    congestion = min(Decimal("100.00"), Decimal(next_count) * Decimal(100) / location.road_capacity)
    rules = {item.scenario: item for item in database.scalars(select(DynamicPricingRule))}
    rule = _rule_for_congestion(rules, congestion)
    normal_amount = rules["normal"].amount
    multiplier = (rule.amount / normal_amount).quantize(Decimal("0.01")) if normal_amount else Decimal("1.00")
    traffic = TrafficRecord(
        location_id=location.id, measured_at=now, simulation_time=now, vehicle_count=next_count,
        road_capacity=location.road_capacity, congestion_percentage=congestion,
        congestion_category=rule.congestion_category, scenario=rule.scenario,
        source="webcam_alpr", simulation_mode="live_webcam",
    )
    database.add(traffic)
    database.flush()
    database.add(TollPrice(
        traffic_record_id=traffic.id, location_id=location.id, effective_at=now,
        amount=(location.base_toll * multiplier).quantize(Decimal("0.01")),
        congestion_category=rule.congestion_category, rule_version="webcam-v1",
    ))
    database.flush()

"""Read-only live operational telemetry for the administrator overview."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import sin
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.db.session import get_db
from app.models import DetectionRecord, DynamicPricingRule, TollTransaction
from app.services.traffic.simulation import scenario_for_time

router = APIRouter(prefix="/api/live", tags=["live telemetry"], dependencies=[Depends(require_admin)])
MALAYSIA_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")


def _telemetry(now: datetime, rules: dict[str, DynamicPricingRule]) -> dict:
    local = now.astimezone(MALAYSIA_TIMEZONE)
    scenario = scenario_for_time(local)
    ranges = {"normal": (18, 30), "moderate": (35, 60), "peak_hour": (65, 83), "severe": (84, 96)}
    low, high = ranges[scenario]
    wave = (sin((local.minute * 60 + local.second) / 180) + 1) / 2
    congestion = round(low + ((high - low) * wave), 1)
    vehicles_per_hour = round(900 + congestion * 42)
    average_speed = round(max(18, 82 - congestion * 0.62), 1)
    base = Decimal(rules["normal"].amount)
    current = Decimal(rules[scenario].amount)
    multiplier = (current / base).quantize(Decimal("0.01")) if base else Decimal("1.00")
    return {"measured_at": now, "congestion_percentage": congestion, "congestion_category": scenario, "vehicle_count": vehicles_per_hour, "road_capacity": 5000, "vehicles_per_hour": vehicles_per_hour, "average_speed_kmh": average_speed, "base_toll_price": base, "congestion_multiplier": multiplier, "current_toll_price": current, "plaza_status": "operational", "camera_status": "online", "system_status": "healthy"}


@router.get("/overview")
def live_overview(database: Session = Depends(get_db)):
    """Return live time-patterned telemetry and persisted ALPR/payment activity.

    This endpoint does not create or update traffic, price, or transaction records.
    """
    now = datetime.now(UTC)
    rules = {item.scenario: item for item in database.scalars(select(DynamicPricingRule))}
    if not {"normal", "moderate", "peak_hour", "severe"}.issubset(rules):
        return {"live": {"traffic": None, "price": None}, "metrics": {}, "traffic_series": [], "price_series": [], "detections": {"items": [], "has_more": False}, "transactions": {"items": [], "has_more": False}}
    telemetry = _telemetry(now, rules)
    hour_ago = now - timedelta(hours=1)
    all_detections = list(database.scalars(select(DetectionRecord).order_by(DetectionRecord.detected_at.desc())))
    all_transactions = list(database.scalars(select(TollTransaction).order_by(TollTransaction.processed_at.desc())))
    detections = all_detections[:12]
    transactions = all_transactions[:12]
    hourly_detections = [item for item in all_detections if item.detected_at >= hour_ago]
    accepted = [item for item in hourly_detections if item.status == "accepted"]
    successful_transactions = [item for item in all_transactions if item.status == "successful" and item.processed_at >= hour_ago]
    average_confidence = sum((item.ocr_confidence or item.detection_confidence) for item in hourly_detections) / len(hourly_detections) if hourly_detections else None
    traffic_series = []
    for offset in range(11, -1, -1):
        sample = _telemetry(now - timedelta(minutes=offset * 5), rules)
        traffic_series.append({"measured_at": sample["measured_at"], "congestion_percentage": sample["congestion_percentage"]})
    return {
        "live": {"traffic": telemetry, "price": {"amount": telemetry["current_toll_price"], "base_amount": telemetry["base_toll_price"], "multiplier": telemetry["congestion_multiplier"]}},
        "metrics": {"detections": len(all_detections), "detections_this_hour": len(hourly_detections), "transactions": len(successful_transactions), "successful_transactions": len(successful_transactions), "failed_transactions": len(hourly_detections) - len(accepted), "revenue": sum((item.amount for item in successful_transactions), Decimal(0)), "average_recognition_confidence": average_confidence},
        "traffic_series": traffic_series, "price_series": [{"effective_at": item["measured_at"], "amount": telemetry["current_toll_price"]} for item in traffic_series],
        "detections": {"items": [{"id": item.id, "detected_at": item.detected_at, "normalized_plate": item.normalized_plate, "status": item.status, "vehicle_id": item.vehicle_id, "detection_confidence": item.detection_confidence, "ocr_confidence": item.ocr_confidence} for item in detections], "has_more": False},
        "transactions": {"items": [{"id": item.id, "processed_at": item.processed_at, "amount": item.amount, "status": item.status, "vehicle_id": item.vehicle_id, "balance_after": item.balance_after} for item in transactions], "has_more": False},
    }

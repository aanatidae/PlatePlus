"""Read-only administrator dashboard data for the simulated prototype."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.db.session import get_db
from app.models import DetectionRecord, TollPrice, TollTransaction, TrafficRecord

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(require_admin)])
DatabaseSession = Annotated[Session, Depends(get_db)]
MALAYSIA_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")


def _in_range(value: datetime, start_at: datetime, end_at: datetime) -> bool:
    return start_at <= value.astimezone(UTC) <= end_at


@router.get("/overview")
def overview(
    database: DatabaseSession,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    congestion_category: str | None = None,
    plate: str | None = None,
    detection_status: str | None = None,
    registration: str | None = Query(default=None, pattern="^(registered|unknown)?$"),
    transaction_status: str | None = None,
    minimum_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    detection_offset: int = Query(default=0, ge=0),
    transaction_offset: int = Query(default=0, ge=0),
    limit: int = Query(default=8, ge=1, le=50),
):
    """Return live state plus Malaysia-time-filtered dashboard history."""
    end = (end_at or datetime.now(UTC)).astimezone(UTC)
    start = (start_at or end - timedelta(days=1)).astimezone(UTC)
    traffic = list(database.scalars(select(TrafficRecord).order_by(TrafficRecord.measured_at.desc())))
    prices = list(database.scalars(select(TollPrice).order_by(TollPrice.effective_at.desc())))
    detections = list(database.scalars(select(DetectionRecord).order_by(DetectionRecord.detected_at.desc())))
    transactions = list(database.scalars(select(TollTransaction).order_by(TollTransaction.processed_at.desc())))
    live_traffic = traffic[0] if traffic else None
    live_price = prices[0] if prices else None
    traffic_history = [item for item in traffic if _in_range(item.measured_at, start, end) and (not congestion_category or item.congestion_category == congestion_category)]
    price_history = [item for item in prices if _in_range(item.effective_at, start, end) and (not congestion_category or item.congestion_category == congestion_category)]
    filtered_detections = [
        item for item in detections
        if _in_range(item.detected_at, start, end)
        and (not plate or plate.upper() in (item.normalized_plate or ""))
        and (not detection_status or item.status == detection_status)
        and (not registration or (item.vehicle_id is not None) == (registration == "registered"))
    ]
    filtered_transactions = [
        item for item in transactions
        if _in_range(item.processed_at, start, end)
        and (not transaction_status or item.status == transaction_status)
        and (minimum_amount is None or item.amount >= minimum_amount)
    ]
    successful = [item for item in filtered_transactions if item.status == "successful"]
    average_confidence = (
        sum((item.ocr_confidence or item.detection_confidence) for item in filtered_detections)
        / len(filtered_detections)
        if filtered_detections else None
    )

    def traffic_item(item: TrafficRecord) -> dict:
        return {"measured_at": item.measured_at, "congestion_percentage": item.congestion_percentage, "congestion_category": item.congestion_category, "vehicle_count": item.vehicle_count, "road_capacity": item.road_capacity}

    def price_item(item: TollPrice) -> dict:
        return {"effective_at": item.effective_at, "amount": item.amount, "congestion_category": item.congestion_category}

    def detection_item(item: DetectionRecord) -> dict:
        return {"id": item.id, "detected_at": item.detected_at, "normalized_plate": item.normalized_plate, "status": item.status, "vehicle_id": item.vehicle_id, "detection_confidence": item.detection_confidence, "ocr_confidence": item.ocr_confidence}

    def transaction_item(item: TollTransaction) -> dict:
        return {"id": item.id, "processed_at": item.processed_at, "amount": item.amount, "status": item.status, "vehicle_id": item.vehicle_id, "balance_after": item.balance_after}

    return {
        "timezone": "Asia/Kuala_Lumpur",
        "live": {"traffic": traffic_item(live_traffic) if live_traffic else None, "price": price_item(live_price) if live_price else None},
        "metrics": {"detections": len(filtered_detections), "transactions": len(filtered_transactions), "successful_transactions": len(successful), "failed_transactions": len(filtered_transactions) - len(successful), "revenue": sum((item.amount for item in successful), Decimal(0)), "average_recognition_confidence": average_confidence},
        "traffic_series": [traffic_item(item) for item in reversed(traffic_history)],
        "price_series": [price_item(item) for item in reversed(price_history)],
        "detections": {"items": [detection_item(item) for item in filtered_detections[detection_offset:detection_offset + limit]], "has_more": detection_offset + limit < len(filtered_detections)},
        "transactions": {"items": [transaction_item(item) for item in filtered_transactions[transaction_offset:transaction_offset + limit]], "has_more": transaction_offset + limit < len(filtered_transactions)},
    }

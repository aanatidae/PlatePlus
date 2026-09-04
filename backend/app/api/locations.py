"""Read-only toll-location metadata endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.api.live import _telemetry
from app.db.session import get_db
from app.models import (
    DetectionRecord,
    DynamicPricingRule,
    TollLocation,
    TollPrice,
    TollTransaction,
    TrafficRecord,
)
from app.schemas.locations import TollLocationRead

router = APIRouter(
    prefix="/api/locations", tags=["toll locations"], dependencies=[Depends(require_admin)]
)
DatabaseSession = Annotated[Session, Depends(get_db)]


def require_location(database: Session, location_id: UUID) -> TollLocation:
    location = database.get(TollLocation, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Toll location was not found.")
    return location


@router.get("", response_model=list[TollLocationRead])
def list_locations(database: DatabaseSession):
    return list(database.scalars(select(TollLocation).order_by(TollLocation.display_name)))


@router.get("/{location_id}", response_model=TollLocationRead)
def get_location(location_id: UUID, database: DatabaseSession):
    return require_location(database, location_id)


def _state(database: Session, location: TollLocation) -> dict:
    now = datetime.now(UTC)
    rules = {item.scenario: item for item in database.scalars(select(DynamicPricingRule))}
    if not {"normal", "moderate", "peak_hour", "severe"}.issubset(rules):
        return {
            "location": location,
            "telemetry": None,
            "telemetry_source": "unavailable",
            "metrics": {},
        }
    fallback = _telemetry(now, rules)
    fallback["road_capacity"] = location.road_capacity
    fallback["vehicle_count"] = round(
        location.road_capacity * fallback["congestion_percentage"] / 100
    )
    fallback["vehicles_per_hour"] = fallback["vehicle_count"]
    fallback["base_toll_price"] = location.base_toll
    fallback["current_toll_price"] = (
        location.base_toll * fallback["congestion_multiplier"]
    ).quantize(Decimal("0.01"))
    traffic = database.scalar(
        select(TrafficRecord)
        .where(TrafficRecord.location_id == location.id)
        .order_by(TrafficRecord.measured_at.desc())
    )
    price = database.scalar(
        select(TollPrice)
        .where(TollPrice.location_id == location.id)
        .order_by(TollPrice.effective_at.desc())
    )
    source = "fallback"
    if traffic:
        fallback.update(
            {
                "measured_at": traffic.measured_at,
                "vehicle_count": traffic.vehicle_count,
                "vehicles_per_hour": traffic.vehicle_count,
                "road_capacity": traffic.road_capacity,
                "congestion_percentage": traffic.congestion_percentage,
                "congestion_category": traffic.congestion_category,
            }
        )
        source = "persisted"
    if price:
        fallback["current_toll_price"] = price.amount
        source = "persisted" if traffic else "mixed"
    hour_ago = now - timedelta(hours=1)
    detections = list(
        database.scalars(
            select(DetectionRecord).where(
                DetectionRecord.location_id == location.id, DetectionRecord.detected_at >= hour_ago
            )
        )
    )
    transactions = list(
        database.scalars(
            select(TollTransaction).where(
                TollTransaction.location_id == location.id, TollTransaction.processed_at >= hour_ago
            )
        )
    )
    successful = [item for item in transactions if item.status == "successful"]
    return {
        "location": location,
        "telemetry": fallback,
        "telemetry_source": source,
        "metrics": {
            "detections": len(detections),
            "transactions": len(transactions),
            "successful_transactions": len(successful),
            "revenue": sum((item.amount for item in successful), Decimal(0)),
        },
    }


@router.get("/network/live")
def network_live(database: DatabaseSession):
    states = [_state(database, item) for item in database.scalars(select(TollLocation))]
    active = [item for item in states if item["telemetry"]]
    capacity = sum(item["telemetry"]["road_capacity"] for item in active)
    return {
        "scope": "all_locations",
        "locations": [
            {
                "id": item["location"].id,
                "code": item["location"].code,
                "telemetry": item["telemetry"],
                "telemetry_source": item["telemetry_source"],
            }
            for item in states
        ],
        "metrics": {
            "traffic_flow": sum(item["telemetry"]["vehicles_per_hour"] for item in active),
            "average_congestion": sum(
                item["telemetry"]["congestion_percentage"] * item["telemetry"]["road_capacity"]
                for item in active
            )
            / capacity
            if capacity
            else None,
            "average_current_toll": sum(item["telemetry"]["current_toll_price"] for item in active)
            / len(active)
            if active
            else None,
            "detections": sum(item["metrics"].get("detections", 0) for item in states),
            "transactions": sum(item["metrics"].get("transactions", 0) for item in states),
            "successful_transactions": sum(
                item["metrics"].get("successful_transactions", 0) for item in states
            ),
            "revenue": sum(
                (item["metrics"].get("revenue", Decimal(0)) for item in states), Decimal(0)
            ),
        },
    }


@router.get("/{location_id}/live")
def location_live(location_id: UUID, database: DatabaseSession):
    state = _state(database, require_location(database, location_id))
    return {
        "scope": "location",
        "location": TollLocationRead.model_validate(state["location"]),
        "telemetry": state["telemetry"],
        "telemetry_source": state["telemetry_source"],
        "metrics": state["metrics"],
    }

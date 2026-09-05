"""Read-only, location-scoped monitoring with explicitly labelled network averages."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DetectionRecord, TollLocation, TollTransaction
from app.schemas.database import DetectionRecordRead, TollTransactionRead
from app.schemas.locations import TollLocationRead


def scoped_overview(database: Session, location_id: UUID | None) -> dict:
    from app.api.locations import _state, require_location

    now = datetime.now(UTC)
    locations = (
        [require_location(database, location_id)]
        if location_id
        else list(database.scalars(select(TollLocation).order_by(TollLocation.display_name)))
    )
    states = [_state(database, location) for location in locations]
    active = [state["telemetry"] for state in states if state["telemetry"]]
    ids = [location.id for location in locations]
    hour_ago = now - timedelta(hours=1)
    detection_scope = [
        DetectionRecord.location_id.in_(ids),
        DetectionRecord.detected_at >= hour_ago,
    ]
    transaction_scope = [
        TollTransaction.location_id.in_(ids),
        TollTransaction.processed_at >= hour_ago,
    ]
    detections = list(
        database.scalars(
            select(DetectionRecord)
            .where(*detection_scope)
            .order_by(DetectionRecord.detected_at.desc())
            .limit(12)
        )
    )
    transactions = list(
        database.scalars(
            select(TollTransaction)
            .where(*transaction_scope)
            .order_by(TollTransaction.processed_at.desc())
            .limit(12)
        )
    )
    count, confidence = database.execute(
        select(
            func.count(DetectionRecord.id),
            func.avg(
                func.coalesce(DetectionRecord.ocr_confidence, DetectionRecord.detection_confidence)
            ),
        ).where(*detection_scope)
    ).one()
    transaction_count = database.scalar(
        select(func.count(TollTransaction.id)).where(*transaction_scope)
    )
    successful, revenue = database.execute(
        select(
            func.count(TollTransaction.id), func.coalesce(func.sum(TollTransaction.amount), 0)
        ).where(*transaction_scope, TollTransaction.status == "successful")
    ).one()
    capacity = sum(item["road_capacity"] for item in active)
    flow = sum(item["vehicles_per_hour"] for item in active)
    congestion = (
        (
            sum(
                Decimal(str(item["congestion_percentage"])) * item["road_capacity"]
                for item in active
            )
            / capacity
        )
        if capacity
        else None
    )
    traffic = active[0] if location_id and active else None
    speed_reporting = [item for item in active if item["average_speed_kmh"] is not None]
    speed_capacity = sum(item["road_capacity"] for item in speed_reporting)
    if not location_id and active:
        traffic = {
            "measured_at": min(item["measured_at"] for item in active),
            "congestion_percentage": congestion,
            "congestion_category": "network average",
            "vehicle_count": flow,
            "vehicles_per_hour": flow,
            "road_capacity": capacity,
            "average_speed_kmh": sum(
                Decimal(str(item["average_speed_kmh"])) * item["road_capacity"] for item in speed_reporting
            ) / speed_capacity
            if speed_capacity
            else None,
        }
    price = (
        {
            "amount": active[0]["current_toll_price"],
            "base_amount": active[0]["base_toll_price"],
            "multiplier": active[0]["congestion_multiplier"],
        }
        if location_id and active
        else {"amount": sum(item["current_toll_price"] for item in active) / len(active)}
        if active
        else None
    )
    return {
        "scope": "location" if location_id else "all_locations",
        "location_id": location_id,
        "generated_at": now,
        "metrics_window": "last_hour",
        "locations": [
            {
                "location": TollLocationRead.model_validate(state["location"]),
                "telemetry": state["telemetry"],
                "telemetry_source": state["telemetry_source"],
            }
            for state in states
        ],
        "live": {"traffic": traffic, "price": price},
        "metrics": {
            "detections": count,
            "detections_this_hour": count,
            "transactions": transaction_count,
            "successful_transactions": successful,
            "failed_transactions": transaction_count - successful,
            "revenue": revenue,
            "average_recognition_confidence": confidence,
            "locations_online": sum(location.status == "operational" for location in locations),
            "locations_total": len(locations),
            "locations_reporting": len(active),
            "severe_locations": sum(float(item["congestion_percentage"]) > 80 for item in active),
            "cameras_offline": sum(item.get("camera_status") == "offline" for item in active),
        },
        "traffic_series": [],
        "price_series": [],
        "detections": {
            "items": [DetectionRecordRead.model_validate(item) for item in detections],
            "has_more": False,
        },
        "transactions": {
            "items": [TollTransactionRead.model_validate(item) for item in transactions],
            "has_more": False,
        },
    }

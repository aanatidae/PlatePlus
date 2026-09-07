"""Read-only evidence and decision traces for the AI Intelligence page."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.api.locations import _state, require_location
from app.api.traffic import _settings
from app.core.settings import Settings
from app.db.session import get_db
from app.models import DetectionRecord, DynamicPricingRule, TollTransaction

router = APIRouter(
    prefix="/api/intelligence", tags=["AI intelligence"], dependencies=[Depends(require_admin)]
)
DatabaseSession = Annotated[Session, Depends(get_db)]


def _result(passed: bool | None, passed_label: str, failed_label: str) -> str:
    if passed is None:
        return "not available"
    return passed_label if passed else failed_label


@router.get("/summary")
def intelligence_summary(database: DatabaseSession, location_id: UUID | None = None):
    """Expose recorded evidence without rerunning models or mutating operational data."""
    app_settings = Settings()
    traffic_settings = _settings(database)
    detection_query = select(DetectionRecord).order_by(DetectionRecord.detected_at.desc())
    if location_id is not None:
        location = require_location(database, location_id)
        detection_query = detection_query.where(DetectionRecord.location_id == location.id)
    else:
        location = None
    detection = database.scalar(detection_query.limit(1))
    transaction = (
        database.scalar(
            select(TollTransaction)
            .where(TollTransaction.detection_id == detection.id)
            .order_by(TollTransaction.processed_at.desc())
        )
        if detection is not None
        else None
    )

    alpr_trace = None
    if detection is not None:
        detector_passed = float(detection.detection_confidence) >= app_settings.detection_confidence_threshold
        ocr_passed = (
            float(detection.ocr_confidence) >= app_settings.ocr_confidence_threshold
            if detection.ocr_confidence is not None
            else None
        )
        alpr_trace = {
            "detected_at": detection.detected_at,
            "source": detection.source,
            "stages": [
                {
                    "name": "Detector result",
                    "detail": "YOLO located a candidate car-plate region.",
                    "value": detection.detection_confidence,
                    "threshold": app_settings.detection_confidence_threshold,
                    "result": _result(detector_passed, "passed", "below detection threshold"),
                },
                {
                    "name": "OCR raw result",
                    "detail": detection.raw_plate_text or "No readable characters were returned.",
                    "value": detection.ocr_confidence,
                    "threshold": app_settings.ocr_confidence_threshold,
                    "result": _result(ocr_passed, "passed", "below OCR threshold"),
                },
                {
                    "name": "Normalization",
                    "detail": detection.normalized_plate or "No normalized Malaysian plate was retained.",
                    "result": "normalized" if detection.normalized_plate else "not accepted",
                },
                {
                    "name": "Charge eligibility",
                    "detail": "Both confidence gates must pass before a registered vehicle can be charged.",
                    "result": "eligible" if detection.status == "accepted" else "not eligible",
                },
                {
                    "name": "Vehicle match",
                    "detail": "Registered vehicle found." if detection.vehicle_id else "No registered vehicle matched this plate.",
                    "result": "matched" if detection.vehicle_id else "unknown vehicle",
                },
                {
                    "name": "Simulated payment",
                    "detail": (
                        f"RM{transaction.amount:.2f} · {transaction.status.replace('_', ' ')}"
                        if transaction is not None
                        else "No payment record was created."
                    ),
                    "result": transaction.status.replace("_", " ") if transaction else "not attempted",
                },
            ],
        }

    pricing_trace = None
    if location is not None:
        state = _state(database, location)
        telemetry = state["telemetry"]
        rules = {item.scenario: item for item in database.scalars(select(DynamicPricingRule))}
        rule = rules.get(telemetry["congestion_category"]) if telemetry else None
        pricing_trace = {
            "location_name": location.display_name,
            "telemetry_source": state["telemetry_source"],
            "traffic": telemetry,
            "policy": {
                "rule_version": traffic_settings.pricing_rule_version,
                "base_toll": location.base_toll,
                "minimum_toll": traffic_settings.minimum_toll,
                "maximum_multiplier": traffic_settings.maximum_toll_multiplier,
                "minimum_change_minutes": traffic_settings.minimum_price_change_minutes,
                "hysteresis_percentage": traffic_settings.pricing_hysteresis_percentage,
                "band": rule.congestion_category if rule else None,
                "band_multiplier": rule.multiplier if rule else None,
            },
            "resulting_toll": telemetry["current_toll_price"] if telemetry else None,
        }

    return {
        "thresholds": {
            "detection": app_settings.detection_confidence_threshold,
            "ocr": app_settings.ocr_confidence_threshold,
        },
        "evaluation": {
            "detector": {
                "accuracy_percent": 93.1,
                "precision": None,
                "recall": None,
                "f1": None,
                "note": "Reported held-out detector accuracy. Precision, recall, and F1 were not exported for this training run and are intentionally not estimated.",
            },
            "ocr": {
                "exact_matches": 37,
                "held_out_samples": 44,
                "exact_match_accuracy_percent": 84.1,
                "note": "PaddleOCR exact-match result on the preserved held-out crop set.",
            },
        },
        "charge_eligibility": "A plate is charge eligible only after detection and OCR meet their active thresholds, normalization retains a plate value, and a registered vehicle is matched. Payment remains simulated and may still fail for account or duplicate-protection reasons.",
        "alpr_trace": alpr_trace,
        "pricing_trace": pricing_trace,
        "known_failure_conditions": [
            "Low light, motion blur, oblique views, occlusion, glare, and unusually formatted plates can reduce detection or OCR reliability.",
            "Similar characters such as 0/O, 1/I, 5/S, 8/B, and 2/Z can be confused by OCR; PlatePlus does not silently substitute characters.",
            "A confidence threshold is a safety gate, not a guarantee that an accepted plate is correct.",
        ],
    }

"""API response schemas for local webcam ALPR."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WebcamBoundingBox(BaseModel):
    left: int
    top: int
    right: int
    bottom: int


class WebcamFrameResult(BaseModel):
    status: str
    message: str
    plate_text: str | None = None
    plate_origin: str = "unknown"
    origin_reason: str | None = None
    recognition_source: str = "local_alpr"
    origin_source: str = "local_rules"
    origin_country: str | None = None
    fallback_used: bool = False
    fallback_provider: str | None = None
    fallback_status: str = "not_requested"
    detection_confidence: float | None = Field(default=None, ge=0, le=1)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    bounding_box: WebcamBoundingBox | None = None
    charge_eligible: bool = False
    cooldown_remaining_seconds: float | None = Field(default=None, ge=0)
    payment_status: str | None = None
    payment_amount: float | None = Field(default=None, ge=0)
    payment_dynamic_toll_amount: float | None = Field(default=None, ge=0)
    payment_foreign_vehicle_charge: float | None = Field(default=None, ge=0)
    payment_balance_after: float | None = Field(default=None, ge=0)
    payment_duplicate: bool = False

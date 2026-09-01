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
    detection_confidence: float | None = Field(default=None, ge=0, le=1)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    bounding_box: WebcamBoundingBox | None = None
    charge_eligible: bool = False
    cooldown_remaining_seconds: float | None = Field(default=None, ge=0)

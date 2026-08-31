"""Domain models for the still-image license-plate pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """Pixel coordinates with an exclusive right and bottom edge."""

    left: int
    top: int
    right: int
    bottom: int

    def width(self) -> int:
        return self.right - self.left

    def height(self) -> int:
        return self.bottom - self.top


@dataclass(frozen=True)
class PlateDetection:
    bounding_box: BoundingBox
    confidence: float
    class_name: str = "car plate"


@dataclass(frozen=True)
class PlateCrop:
    image: object
    bounding_box: BoundingBox
    detection_confidence: float


@dataclass(frozen=True)
class OcrResult:
    raw_text: str
    normalized_text: str
    confidence: float


@dataclass(frozen=True)
class RecognitionDecision:
    accepted: bool
    reason: str | None


def recognition_decision(
    detection_confidence: float,
    ocr_confidence: float,
    detection_threshold: float,
    ocr_threshold: float,
) -> RecognitionDecision:
    """Return the decision that downstream simulated charging must honour."""
    if detection_confidence < detection_threshold:
        return RecognitionDecision(False, "detection_confidence_below_threshold")
    if ocr_confidence < ocr_threshold:
        return RecognitionDecision(False, "ocr_confidence_below_threshold")
    return RecognitionDecision(True, None)
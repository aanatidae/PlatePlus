from __future__ import annotations

import cv2
import numpy as np
import pytest

from alpr.types import BoundingBox, OcrResult, PlateDetection
from app.services.detection.webcam_processor import FrameProcessorError, WebcamFrameProcessor


class _Detector:
    def __init__(self, detections: list[PlateDetection]) -> None:
        self._detections = detections

    def detect(self, image: np.ndarray) -> list[PlateDetection]:
        return self._detections


class _Recognizer:
    def __init__(self, result: OcrResult) -> None:
        self._result = result

    def recognize(self, crop: np.ndarray) -> OcrResult:
        assert crop.size > 0
        return self._result


def _frame_bytes() -> bytes:
    ok, encoded = cv2.imencode(".jpg", np.zeros((80, 160, 3), dtype=np.uint8))
    assert ok
    return encoded.tobytes()


def test_processor_returns_no_plate_status_without_detection() -> None:
    processor = WebcamFrameProcessor(_Detector([]), _Recognizer(OcrResult("", "", 0)), 0.5, 0.7)

    result = processor.process(_frame_bytes())

    assert result.status == "no_plate_detected"
    assert not result.charge_eligible


def test_processor_requires_both_confidence_thresholds() -> None:
    detection = PlateDetection(BoundingBox(20, 20, 100, 45), confidence=0.9)
    processor = WebcamFrameProcessor(
        _Detector([detection]), _Recognizer(OcrResult("BKV 1234", "BKV1234", 0.65)), 0.5, 0.7
    )

    result = processor.process(_frame_bytes())

    assert result.status == "ocr_confidence_below_threshold"
    assert not result.charge_eligible


def test_processor_rejects_invalid_image_bytes() -> None:
    processor = WebcamFrameProcessor(_Detector([]), _Recognizer(OcrResult("", "", 0)), 0.5, 0.7)

    with pytest.raises(FrameProcessorError, match="could not be decoded"):
        processor.process(b"not-an-image")

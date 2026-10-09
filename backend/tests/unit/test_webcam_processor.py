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
    assert result.plate_origin == "unknown"
    assert result.origin_reason == "not_evaluated_below_confidence"
    assert not result.charge_eligible


def test_processor_rejects_an_implausible_plate_after_confidence_gates() -> None:
    detection = PlateDetection(BoundingBox(20, 20, 100, 45), confidence=0.9)
    processor = WebcamFrameProcessor(
        _Detector([detection]), _Recognizer(OcrResult("ABCDEF", "ABCDEF", 0.95)), 0.5, 0.7
    )

    result = processor.process(_frame_bytes())

    assert result.status == "unsupported_plate_origin"
    assert not result.charge_eligible


@pytest.mark.parametrize(
    ("plate", "expected_origin", "eligible"),
    [
        ("BKV1234", "malaysian", True),
        ("GBC1234R", "singaporean", True),
        ("SLP1234A", "unknown", False),
    ],
)
def test_processor_classifies_origin_after_confidence_gates(
    plate: str, expected_origin: str, eligible: bool
) -> None:
    detection = PlateDetection(BoundingBox(20, 20, 100, 45), confidence=0.9)
    processor = WebcamFrameProcessor(
        _Detector([detection]), _Recognizer(OcrResult(plate, plate, 0.95)), 0.5, 0.7
    )

    result = processor.process(_frame_bytes())

    assert result.plate_origin == expected_origin
    assert result.charge_eligible is eligible
    if expected_origin == "unknown":
        assert result.status == "ambiguous_plate_origin"


def test_processor_rejects_invalid_image_bytes() -> None:
    processor = WebcamFrameProcessor(_Detector([]), _Recognizer(OcrResult("", "", 0)), 0.5, 0.7)

    with pytest.raises(FrameProcessorError, match="could not be decoded"):
        processor.process(b"not-an-image")


@pytest.mark.parametrize("failure", [ImportError("DLL load failed"), RuntimeError("inference failed")])
def test_ocr_runtime_failure_is_readable_and_never_reaches_payment(failure) -> None:
    from unittest.mock import patch

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient

    from app.api.auth import require_admin
    from app.api.webcam import router, service
    from app.db.session import get_db

    class BrokenRecognizer:
        def recognize(self, crop):
            raise failure

    processor = WebcamFrameProcessor(
        _Detector([PlateDetection(BoundingBox(20, 20, 100, 45), confidence=0.9)]),
        BrokenRecognizer(), 0.5, 0.7,
    )
    app = FastAPI()
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"])
    app.include_router(router)
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[get_db] = lambda: object()
    with patch.object(service, "_processor", processor), patch(
        "app.api.webcam.process_toll_event"
    ) as payment, TestClient(app) as client:
        response = client.post(
            "/api/webcam/images",
            headers={"Origin": "http://localhost:5173"},
            files={"image": ("plate.jpg", _frame_bytes(), "image/jpeg")},
        )
    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "Local OCR is unavailable" in response.json()["detail"]
    assert "No toll was charged" in response.json()["detail"]
    payment.assert_not_called()

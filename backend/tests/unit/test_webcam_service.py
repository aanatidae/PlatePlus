from __future__ import annotations

from dataclasses import dataclass

from alpr.types import BoundingBox
from app.services.detection.webcam_processor import ProcessedFrame
from app.services.detection.webcam_service import WebcamService


@dataclass
class _FakeProcessor:
    result: ProcessedFrame

    def process(self, frame_bytes: bytes) -> ProcessedFrame:
        assert frame_bytes == b"frame"
        return self.result


def _accepted_result() -> ProcessedFrame:
    return ProcessedFrame(
        status="accepted_for_vehicle_lookup",
        message="Recognition passed confidence checks.",
        plate_text="BKV1234",
        detection_confidence=0.9,
        ocr_confidence=0.9,
        bounding_box=BoundingBox(1, 2, 20, 10),
        charge_eligible=True,
    )


def test_service_rejects_frame_from_unknown_session() -> None:
    service = WebcamService(_FakeProcessor(_accepted_result()), 20, clock=lambda: 10)

    result = service.process_frame("missing", b"frame")

    assert result.status == "webcam_session_not_active"
    assert not result.charge_eligible


def test_service_blocks_repeated_eligible_plate_in_one_session() -> None:
    clock_values = iter([10.0, 11.0, 31.0])
    service = WebcamService(_FakeProcessor(_accepted_result()), 20, clock=lambda: next(clock_values))
    service.start_session("session")

    assert service.process_frame("session", b"frame").charge_eligible
    assert service.process_frame("session", b"frame").status == "duplicate_plate_within_cooldown"
    assert service.process_frame("session", b"frame").charge_eligible


def test_service_does_not_apply_cooldown_to_rejected_recognition() -> None:
    rejected = ProcessedFrame("ocr_confidence_below_threshold", "Rejected", plate_text="BKV1234")
    service = WebcamService(_FakeProcessor(rejected), 20, clock=lambda: 10)
    service.start_session("session")

    assert service.process_frame("session", b"frame").status == "ocr_confidence_below_threshold"

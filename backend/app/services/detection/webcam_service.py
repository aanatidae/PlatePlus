"""Session-aware service for browser webcam frames."""

from __future__ import annotations

from collections.abc import Callable
from time import monotonic

from alpr.webcam import WebcamSession

from app.services.detection.webcam_processor import ProcessedFrame, WebcamFrameProcessor


class WebcamService:
    """Manage local browser sessions and prevent repeated eligible events."""

    def __init__(
        self,
        processor: WebcamFrameProcessor,
        duplicate_cooldown_seconds: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._processor = processor
        self._cooldown = duplicate_cooldown_seconds
        self._clock = clock
        self._sessions: dict[str, WebcamSession] = {}

    def start_session(self, session_id: str) -> None:
        session = WebcamSession(self._cooldown)
        session.start()
        self._sessions[session_id] = session

    def stop_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            session.stop()

    def process_frame(self, session_id: str, frame_bytes: bytes) -> ProcessedFrame:
        session = self._sessions.get(session_id)
        if session is None:
            return ProcessedFrame("webcam_session_not_active", "Start a webcam session before sending frames.")

        result = self._processor.process(frame_bytes)
        if not result.charge_eligible or not result.plate_text:
            return result
        gate = session.allow_recognition(result.plate_text, observed_at=self._clock())
        if gate.accepted:
            return result
        return ProcessedFrame(
            status=gate.reason or "duplicate_plate_within_cooldown",
            message="This plate was already processed recently in this webcam session.",
            plate_text=result.plate_text,
            detection_confidence=result.detection_confidence,
            ocr_confidence=result.ocr_confidence,
            bounding_box=result.bounding_box,
            charge_eligible=False,
        )

    def process_image(self, image_bytes: bytes) -> ProcessedFrame:
        """Process one operator-uploaded still image without webcam-session cooldowns.

        An upload is a distinct, intentional toll-event submission. Database
        idempotency protects its payment flow; webcam-only cooldown state must
        not leak into it.
        """
        return self._processor.process(image_bytes)

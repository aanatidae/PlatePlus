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
        self._session_sources: dict[str, str] = {}
        self._last_frame_at: dict[str, float] = {}

    def start_session(self, session_id: str, *, source: str = "laptop") -> None:
        if source not in {"laptop", "phone"}:
            raise ValueError("Camera source must be laptop or phone.")
        session = WebcamSession(self._cooldown)
        session.start()
        self._sessions[session_id] = session
        self._session_sources[session_id] = source
        # A connected source means it is actually sending sampled frames, not
        # merely that a browser opened a session.
        self._last_frame_at[session_id] = float("-inf")

    def stop_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        self._session_sources.pop(session_id, None)
        self._last_frame_at.pop(session_id, None)
        if session is not None:
            session.stop()

    def process_frame(self, session_id: str, frame_bytes: bytes) -> ProcessedFrame:
        session = self._sessions.get(session_id)
        if session is None:
            return ProcessedFrame("webcam_session_not_active", "Start a webcam session before sending frames.")
        observed_at = self._clock()
        self._last_frame_at[session_id] = observed_at

        result = self._processor.process(frame_bytes)
        if not result.charge_eligible or not result.plate_text:
            return result
        gate = session.allow_recognition(result.plate_text, observed_at=observed_at)
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

    def source_for_session(self, session_id: str) -> str | None:
        return self._session_sources.get(session_id)

    def active_sources(self, *, stale_after_seconds: float = 5.0) -> set[str]:
        now = self._clock()
        return {
            self._session_sources[session_id]
            for session_id, last_seen in self._last_frame_at.items()
            if session_id in self._sessions and now - last_seen <= stale_after_seconds
        }

    def process_image(self, image_bytes: bytes) -> ProcessedFrame:
        """Process one operator-uploaded still image without webcam-session cooldowns.

        An upload is a distinct, intentional toll-event submission. Database
        idempotency protects its payment flow; webcam-only cooldown state must
        not leak into it.
        """
        return self._processor.process(image_bytes)

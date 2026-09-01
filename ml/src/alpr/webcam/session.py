"""Session-scoped safeguards for repeated webcam observations."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class WebcamSessionDecision:
    """Whether an accepted recognition may advance to downstream processing."""

    accepted: bool
    reason: str | None = None


class WebcamSession:
    """Keep duplicate plate observations from causing repeat live-toll events.

    This object retains only normalized plate strings and monotonic timestamps for
    the lifetime of one local webcam session. It never stores camera frames or
    crops. Persistence and the final transaction idempotency check remain the
    responsibility of the backend transaction service.
    """

    def __init__(self, duplicate_cooldown_seconds: float = 20.0) -> None:
        if duplicate_cooldown_seconds <= 0:
            raise ValueError("duplicate_cooldown_seconds must be greater than zero")
        self._duplicate_cooldown_seconds = duplicate_cooldown_seconds
        self._started = False
        self._observed_at: dict[str, float] = {}

    @property
    def active(self) -> bool:
        return self._started

    def start(self) -> None:
        """Start a fresh local session without retaining prior observations."""
        self._started = True
        self._observed_at.clear()

    def stop(self) -> None:
        """End the session and discard its in-memory plate observation history."""
        self._started = False
        self._observed_at.clear()

    def allow_recognition(self, normalized_plate: str, observed_at: float | None = None) -> WebcamSessionDecision:
        """Accept a new recognized plate unless it is inside this session's cooldown."""
        if not self._started:
            return WebcamSessionDecision(False, "webcam_session_not_active")
        if not normalized_plate:
            return WebcamSessionDecision(False, "plate_text_empty")

        now = monotonic() if observed_at is None else observed_at
        previous = self._observed_at.get(normalized_plate)
        if previous is not None and now - previous < self._duplicate_cooldown_seconds:
            return WebcamSessionDecision(False, "duplicate_plate_within_cooldown")

        self._observed_at[normalized_plate] = now
        self._prune_expired(now)
        return WebcamSessionDecision(True)

    def _prune_expired(self, now: float) -> None:
        self._observed_at = {
            plate: observed
            for plate, observed in self._observed_at.items()
            if now - observed < self._duplicate_cooldown_seconds
        }

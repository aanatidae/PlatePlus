from __future__ import annotations

import pytest

from alpr.webcam import WebcamSession


def test_session_must_be_started_before_recognition_can_progress() -> None:
    session = WebcamSession()

    assert session.allow_recognition("BKV1234", observed_at=10.0).reason == "webcam_session_not_active"


def test_session_blocks_a_repeated_plate_during_the_cooldown() -> None:
    session = WebcamSession(duplicate_cooldown_seconds=20)
    session.start()

    assert session.allow_recognition("BKV1234", observed_at=10.0).accepted
    assert session.allow_recognition("BKV1234", observed_at=29.9).reason == "duplicate_plate_within_cooldown"
    assert session.allow_recognition("BKV1234", observed_at=30.0).accepted


def test_stop_discards_plate_history_for_the_next_session() -> None:
    session = WebcamSession()
    session.start()
    assert session.allow_recognition("BKV1234", observed_at=10.0).accepted

    session.stop()
    session.start()

    assert session.allow_recognition("BKV1234", observed_at=11.0).accepted


@pytest.mark.parametrize("cooldown", [0, -1])
def test_session_rejects_non_positive_cooldown(cooldown: float) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        WebcamSession(duplicate_cooldown_seconds=cooldown)

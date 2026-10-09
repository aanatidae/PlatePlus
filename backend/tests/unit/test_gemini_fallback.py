from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import cv2
import numpy as np
import pytest
from alpr.types import BoundingBox

from app.core.settings import Settings
from app.services.detection.gemini_fallback import (
    GeminiFallback,
    GeminiPlateResult,
    GooglePlateProvider,
    validate_result,
)
from app.services.detection.webcam_processor import ProcessedFrame


@pytest.fixture(autouse=True)
def isolated_key(monkeypatch):
    # Deliberately fictional test token; never load the user's private .env.
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-private-token")
    monkeypatch.setattr("app.services.detection.gemini_fallback.load_dotenv", lambda *a, **k: None)


def image():
    return cv2.imencode(".png", np.zeros((100, 200, 3), dtype=np.uint8))[1].tobytes()


def answer(plate="SJG6821C", origin="singaporean", country="Singapore", **kwargs):
    return GeminiPlateResult(plate_detected=True, plate_text=plate, origin=origin,
                             country=country, confidence="high", reason="Visible plate", **kwargs)


def fallback(provider, enabled=True):
    return GeminiFallback(Settings(enable_gemini_fallback=enabled, _env_file=None), provider)


@pytest.mark.parametrize("status", ["accepted_for_vehicle_lookup", "duplicate_plate_within_cooldown",
                                   "insufficient_balance", "ocr_confidence_below_threshold",
                                   "unsupported_plate_origin", "webcam_session_not_active"])
def test_resolved_or_non_recognition_failures_never_call_provider(status):
    provider = SimpleNamespace(recognize=AsyncMock())
    local = ProcessedFrame(status, "Local result", plate_text="VAA1234")
    assert asyncio.run(fallback(provider).resolve(local, image())) == local
    provider.recognize.assert_not_called()


def test_disabled_and_missing_key_do_not_call_provider(monkeypatch):
    provider = SimpleNamespace(recognize=AsyncMock())
    local = ProcessedFrame("no_plate_detected", "Unread")
    assert asyncio.run(fallback(provider, enabled=False).resolve(local, image())) == local
    monkeypatch.delenv("GEMINI_API_KEY")
    result = asyncio.run(fallback(provider).resolve(local, image()))
    assert result.fallback_status == "gemini_unavailable" and not result.charge_eligible
    assert not result.fallback_used
    provider.recognize.assert_not_called()


@pytest.mark.parametrize("status", ["no_plate_detected", "unread_plate", "ocr_unreadable"])
def test_unread_plate_fallback_is_called_once_without_invented_local_confidence(status):
    provider = SimpleNamespace(recognize=AsyncMock(return_value=answer()))
    result = asyncio.run(fallback(provider).resolve(ProcessedFrame(status, "Unread"), image()))
    assert result.plate_text == "SJG6821C" and result.charge_eligible
    assert result.plate_origin == "singaporean" and result.origin_country == "Singapore"
    assert result.recognition_source == "gemini_fallback"
    assert result.detection_confidence is None and result.ocr_confidence is None
    provider.recognize.assert_awaited_once()


def test_overlap_uses_crop_and_preserves_readable_local_text():
    provider = SimpleNamespace(recognize=AsyncMock(return_value=answer()))
    local = ProcessedFrame("ambiguous_plate_origin", "Overlap", plate_text="SJG6821C",
                           bounding_box=BoundingBox(10, 10, 90, 40), detection_confidence=.9,
                           ocr_confidence=.95)
    result = asyncio.run(fallback(provider).resolve(local, image()))
    assert result.recognition_source == "local_alpr" and result.origin_source == "gemini_fallback"
    data, text, overlap = provider.recognize.call_args.args
    assert cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR).shape[:2] == (30, 80)
    assert text == "SJG6821C" and overlap
    provider.recognize.return_value = answer("SJG6822C")
    rejected = asyncio.run(fallback(provider).resolve(local, image()))
    assert rejected.fallback_status == "gemini_unknown" and not rejected.charge_eligible
    assert rejected.plate_text == "SJG6821C"


@pytest.mark.parametrize("update", [
    {"confidence": "medium"}, {"confidence": "low"}, {"plate_detected": False},
    {"origin": "unknown"}, {"country": "Malaysia"}, {"plate_text": "made up prose"},
    {"plate_text": "กข1234"}, {"origin": "malaysian", "plate_text": "GBC1234R"},
    {"origin": "foreign_other", "country": "Thailand"},
])
def test_invalid_or_uncertain_provider_result_is_rejected(update):
    result = answer().model_copy(update=update)
    assert validate_result(result) is None


@pytest.mark.parametrize(("plate", "origin", "country"), [
    ("VAA1234", "malaysian", "Malaysia"), ("GBC1234R", "singaporean", "Singapore"),
    ("AB12CDE", "foreign_other", "United Kingdom"),
])
def test_supported_origins_validate(plate, origin, country):
    assert validate_result(answer(plate, origin, country)).country == country


@pytest.mark.parametrize("failure", [TimeoutError("unit-test-private-token"), RuntimeError("429 unit-test-private-token")])
def test_provider_failures_do_not_leak_error_or_key(failure, caplog):
    provider = SimpleNamespace(recognize=AsyncMock(side_effect=failure))
    result = asyncio.run(fallback(provider).resolve(ProcessedFrame("no_plate_detected", "Unread"), image()))
    assert result.fallback_status == "gemini_unavailable" and not result.charge_eligible
    assert "unit-test-private-token" not in repr(result) + caplog.text


def test_invalid_structured_response_and_image_fail_safely():
    provider = SimpleNamespace(recognize=AsyncMock(return_value={"plate_text": "SJG6821C"}))
    local = ProcessedFrame("no_plate_detected", "Unread")
    assert asyncio.run(fallback(provider).resolve(local, image())).fallback_status == "gemini_unavailable"
    provider.recognize.reset_mock()
    assert asyncio.run(fallback(provider).resolve(local, b"not-an-image")).fallback_status == "gemini_invalid_image"
    provider.recognize.assert_not_called()


def test_total_deadline_cancels_provider_without_retries():
    cancelled = []
    async def slow_provider(*args):
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.append(True)
    provider = SimpleNamespace(recognize=AsyncMock(side_effect=slow_provider))
    service = GeminiFallback(Settings(enable_gemini_fallback=True, gemini_timeout_seconds=1, _env_file=None), provider)
    result = asyncio.run(service.resolve(ProcessedFrame("no_plate_detected", "Unread"), image()))
    assert result.fallback_status == "gemini_unavailable" and not result.charge_eligible
    assert cancelled == [True]
    provider.recognize.assert_awaited_once()


def test_sdk_configuration_uses_backend_key_structured_schema_and_no_retries(monkeypatch):
    import sys

    options = []
    requests = []
    class Client:
        def __init__(self, **kwargs):
            options.append(kwargs)
            self.aio = self
            async def generate(**kwargs):
                requests.append(kwargs)
                return SimpleNamespace(parsed=answer())
            self.models = SimpleNamespace(generate_content=AsyncMock(side_effect=generate))
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
    types = SimpleNamespace(HttpOptions=lambda **kw: kw, HttpRetryOptions=lambda **kw: kw,
                            Part=SimpleNamespace(from_bytes=lambda **kw: kw),
                            GenerateContentConfig=lambda **kw: kw)
    genai = SimpleNamespace(Client=Client, types=types)
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=genai))
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    provider = GooglePlateProvider(Settings(_env_file=None))
    result = asyncio.run(provider.recognize(b"encoded-image", None, False))
    assert result.origin == "singaporean"
    assert options[0]["api_key"] == "unit-test-private-token"
    assert options[0]["http_options"]["timeout"] == 15000
    assert options[0]["http_options"]["retry_options"]["attempts"] == 1
    assert "response_schema" not in requests[0]["config"]
    assert requests[0]["config"]["response_json_schema"] == GeminiPlateResult.model_json_schema()

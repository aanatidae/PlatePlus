from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import cv2
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import webcam
from app.api.auth import router as auth_router
from app.core.settings import Settings
from app.db.session import get_db
from app.models import (
    Account,
    DetectionRecord,
    TollLocation,
    TollPrice,
    TollTransaction,
    User,
    Vehicle,
    WalletLedgerEntry,
)
from app.services.detection.gemini_fallback import GeminiFallback, GeminiPlateResult
from app.services.detection.webcam_processor import ProcessedFrame


@pytest.mark.parametrize(("plate", "origin", "country", "total"), [
    ("SJG6821C", "singaporean", "Singapore", Decimal("22.00")),
    ("VAA1234", "malaysian", "Malaysia", Decimal("2.00")),
    ("AB12CDE", "foreign_other", "United Kingdom", Decimal("22.00")),
])
@pytest.mark.parametrize("local_status", ["no_plate_detected", "ambiguous_plate_origin"])
@pytest.mark.parametrize("prior_count", [0, 3])
def test_mocked_external_upload_runs_safe_itemized_payment_and_replays_without_provider(
    database, admin_auth_headers, monkeypatch, plate, origin, country, total, local_status, prior_count,
):
    location = database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))
    user = User(full_name="Fictional Fallback Driver", email="fallback@example.test")
    database.add(user); database.flush()
    account = Account(user_id=user.id, balance=Decimal("50.00"), is_primary=True)
    vehicle = Vehicle(user_id=user.id, plate_number=plate, registration_origin=origin,
                      origin_country=country if origin == "foreign_other" else None)
    database.add_all([account, vehicle]); database.flush()
    dynamic = Decimal("3.00") if prior_count else Decimal("2.00")
    fee = total - 2
    total = dynamic + fee
    for _ in range(prior_count):
        database.add(DetectionRecord(location_id=location.id, detected_at=datetime.now(UTC)-timedelta(seconds=5), detection_confidence=.9, status="accepted", source="uploaded_image"))
    database.flush()
    local = ProcessedFrame(local_status, "Unresolved", plate_text=plate if local_status == "ambiguous_plate_origin" else None)
    monkeypatch.setattr(webcam, "service", SimpleNamespace(process_image=lambda data: local))
    result = GeminiPlateResult(plate_detected=True, plate_text=plate, origin=origin,
                              country=country, confidence="high", reason="Fictional fixture")
    provider = SimpleNamespace(recognize=AsyncMock(return_value=result))
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-private-token")
    monkeypatch.setattr("app.services.detection.gemini_fallback.load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(webcam, "fallback", GeminiFallback(Settings(enable_gemini_fallback=True, _env_file=None), provider))
    app = FastAPI(); app.include_router(auth_router); app.include_router(webcam.router)
    app.dependency_overrides[get_db] = lambda: database
    payload = cv2.imencode(".png", np.zeros((100, 200, 3), np.uint8))[1].tobytes()
    client = TestClient(app)
    path = f"/api/webcam/images?location_id={location.id}"
    headers = {**admin_auth_headers, "Idempotency-Key": "gemini-mocked-upload-0001"}
    response = client.post(path, files={"image": ("synthetic.png", payload, "image/png")}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["payment_status"] == "successful" and body["plate_text"] == plate
    assert body["plate_origin"] == origin and body["origin_source"] == "gemini_fallback"
    assert body["fallback_used"] and body["payment_amount"] == float(total)
    assert body["payment_dynamic_toll_amount"] == float(dynamic) and body["payment_foreign_vehicle_charge"] == float(fee)
    assert "unit-test-private-token" not in response.text and "GEMINI_API_KEY" not in response.text
    detection = database.scalar(select(DetectionRecord).where(DetectionRecord.normalized_plate == plate))
    transaction = database.scalar(select(TollTransaction).where(TollTransaction.idempotency_key == headers["Idempotency-Key"]))
    assert detection.source == "uploaded_image" and detection.fallback_provider == "gemini"
    assert detection.origin_country == country and detection.fallback_used
    assert detection.recognition_source == ("local_alpr" if local_status == "ambiguous_plate_origin" else "gemini_fallback")
    assert transaction.amount == total and transaction.dynamic_toll_amount == dynamic
    assert transaction.foreign_vehicle_charge == fee
    database.refresh(account); assert account.balance == 50 - total
    ledger = database.scalar(select(WalletLedgerEntry).where(WalletLedgerEntry.transaction_id == transaction.id))
    assert ledger.amount == total
    replay = client.post(path, files={"image": ("synthetic.png", payload, "image/png")}, headers=headers)
    assert replay.json()["payment_duplicate"] and replay.json()["fallback_used"]
    provider.recognize.assert_awaited_once()
    database.refresh(account); assert account.balance == 50 - total


@pytest.mark.parametrize(("case", "expected"), [("unknown", "low_confidence"), ("timeout", "low_confidence"),
                                               ("unregistered", "unknown_vehicle"), ("insufficient", "insufficient_balance"),
                                               ("country_mismatch", "failed")])
def test_fallback_unknown_failure_and_account_safety(database, admin_auth_headers, monkeypatch, case, expected):
    location = database.scalar(select(TollLocation).where(TollLocation.code == "AKLEH"))
    user = User(full_name="Fictional Driver", email="fallback-safe@example.test")
    database.add(user); database.flush()
    account = Account(user_id=user.id, balance=Decimal("1.00") if case == "insufficient" else Decimal("50.00"), is_primary=True)
    plate = "AB12CDE" if case == "country_mismatch" else "SJG6821C"
    origin = "foreign_other" if case == "country_mismatch" else "singaporean"
    country = "United Kingdom" if case == "country_mismatch" else "Singapore"
    if case != "unregistered":
        database.add(Vehicle(user_id=user.id, plate_number=plate, registration_origin=origin,
                             origin_country="other" if case == "country_mismatch" else None))
    database.add_all([account, TollPrice(location_id=location.id, effective_at=datetime.now(UTC)-timedelta(minutes=1),
                                        amount=Decimal("2.00"), congestion_category="low")]); database.flush()
    original = account.balance
    result = GeminiPlateResult(plate_detected=True, plate_text=plate,
                              origin="unknown" if case == "unknown" else origin, country=country,
                              confidence="high", reason="Fixture only")
    provider = SimpleNamespace(recognize=AsyncMock(return_value=result, side_effect=TimeoutError("private-token") if case == "timeout" else None))
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-private-token")
    monkeypatch.setattr("app.services.detection.gemini_fallback.load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(webcam, "service", SimpleNamespace(process_image=lambda data: ProcessedFrame("no_plate_detected", "Unread")))
    monkeypatch.setattr(webcam, "fallback", GeminiFallback(Settings(enable_gemini_fallback=True, _env_file=None), provider))
    app = FastAPI(); app.include_router(auth_router); app.include_router(webcam.router)
    app.dependency_overrides[get_db] = lambda: database
    image = cv2.imencode(".png", np.zeros((20, 30, 3), np.uint8))[1].tobytes()
    response = TestClient(app).post(f"/api/webcam/images?location_id={location.id}",
                                  files={"image": ("synthetic.png", image, "image/png")},
                                  headers={**admin_auth_headers, "Idempotency-Key": "gemini-failure-upload-0001"})
    assert response.status_code == 200, response.text
    assert response.json()["payment_status"] == expected
    database.refresh(account); assert account.balance == original
    assert database.scalar(select(WalletLedgerEntry).where(WalletLedgerEntry.entry_type == "toll_deduction")) is None

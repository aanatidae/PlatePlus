from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import webcam as webcam_api
from app.api.auth import router as auth_router
from app.db.session import get_db
from app.models import Account, DetectionRecord, TollPrice, TollTransaction, User, Vehicle
from app.services.detection.webcam_processor import ProcessedFrame


class _SuccessfulImageService:
    def process_image(self, image_bytes: bytes) -> ProcessedFrame:
        assert image_bytes == b"image-bytes"
        return ProcessedFrame(
            status="accepted_for_vehicle_lookup",
            message="Recognition passed confidence checks.",
            plate_text="VAA1234",
            detection_confidence=0.95,
            ocr_confidence=0.93,
            charge_eligible=True,
        )


def test_authenticated_image_upload_runs_the_complete_simulated_toll_flow(
    database, admin_auth_headers, monkeypatch
) -> None:
    user = User(full_name="Upload Test User", email="upload@example.test")
    database.add(user)
    database.flush()
    account = Account(user_id=user.id, balance=Decimal("20.00"), is_primary=True)
    vehicle = Vehicle(user_id=user.id, plate_number="VAA1234")
    price = TollPrice(
        effective_at=datetime.now(UTC) - timedelta(minutes=1),
        amount=Decimal("2.00"),
        congestion_category="low",
    )
    database.add_all([account, vehicle, price])
    database.flush()

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(webcam_api.router)
    app.dependency_overrides[get_db] = lambda: database
    monkeypatch.setattr(webcam_api, "service", _SuccessfulImageService())

    response = TestClient(app).post(
        "/api/webcam/images",
        files={"image": ("plate.jpg", b"image-bytes", "image/jpeg")},
        headers={**admin_auth_headers, "Idempotency-Key": "upload-e2e-test-0001"},
    )

    database.refresh(account)
    detection = database.scalar(select(DetectionRecord))
    transaction = database.scalar(select(TollTransaction))
    assert response.status_code == 200, response.text
    assert response.json()["payment_status"] == "successful"
    assert account.balance == Decimal("18.00")
    assert detection is not None and detection.source == "upload"
    assert transaction is not None and transaction.status == "successful"


def test_image_upload_requires_administrator_authentication(database, monkeypatch) -> None:
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(webcam_api.router)
    app.dependency_overrides[get_db] = lambda: database
    monkeypatch.setattr(webcam_api, "service", _SuccessfulImageService())

    response = TestClient(app).post(
        "/api/webcam/images",
        files={"image": ("plate.jpg", b"image-bytes", "image/jpeg")},
    )

    assert response.status_code == 401

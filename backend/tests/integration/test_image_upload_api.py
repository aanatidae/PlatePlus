from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import webcam as webcam_api
from app.api.auth import router as auth_router
from app.db.session import get_db
from app.models import (
    Account,
    DetectionRecord,
    TollLocation,
    TollPrice,
    TollTransaction,
    User,
    Vehicle,
)
from app.services.detection.webcam_processor import ProcessedFrame


class _SuccessfulImageService:
    def process_image(self, image_bytes: bytes) -> ProcessedFrame:
        assert image_bytes == b"image-bytes"
        return ProcessedFrame(
            status="accepted_for_vehicle_lookup",
            message="Recognition passed confidence checks.",
            plate_text="VAA1234",
            plate_origin="malaysian",
            origin_reason="malaysian_supported_pattern",
            detection_confidence=0.95,
            ocr_confidence=0.93,
            charge_eligible=True,
        )


class _SuccessfulSingaporeanImageService:
    def process_image(self, image_bytes: bytes) -> ProcessedFrame:
        assert image_bytes == b"image-bytes"
        return ProcessedFrame(
            status="accepted_for_vehicle_lookup",
            message="Recognition passed confidence checks.",
            plate_text="GBC1234R",
            plate_origin="singaporean",
            origin_reason="singaporean_supported_pattern",
            detection_confidence=0.95,
            ocr_confidence=0.93,
            charge_eligible=True,
        )


@pytest.mark.parametrize("selected_location", [False, True])
def test_authenticated_image_upload_runs_the_complete_simulated_toll_flow(
    database, admin_auth_headers, monkeypatch, selected_location
) -> None:
    location = database.scalar(select(TollLocation).where(TollLocation.code == ("DUKE" if selected_location else "PENCHALA")))
    user = User(full_name="Upload Test User", email="upload@example.test")
    database.add(user)
    database.flush()
    account = Account(user_id=user.id, balance=Decimal("20.00"), is_primary=True)
    vehicle = Vehicle(user_id=user.id, plate_number="VAA1234")
    price = TollPrice(
        location_id=location.id,
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
        f"/api/webcam/images?location_id={location.id}" if selected_location else "/api/webcam/images",
        files={"image": ("plate.jpg", b"image-bytes", "image/jpg")},
        headers={**admin_auth_headers, "Idempotency-Key": "upload-e2e-test-0001"},
    )

    database.refresh(account)
    detection = database.scalar(select(DetectionRecord))
    transaction = database.scalar(select(TollTransaction))
    assert response.status_code == 200, response.text
    assert response.json()["payment_status"] == "successful"
    assert response.json()["plate_origin"] == "malaysian"
    assert account.balance == Decimal("18.00")
    assert detection is not None and detection.source == "upload"
    assert transaction is not None and transaction.status == "successful"
    assert detection.location_id == transaction.location_id == location.id


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


def test_simulator_upload_is_tagged_and_drives_one_local_crossing(
    database, admin_auth_headers, monkeypatch
) -> None:
    location = database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))
    assert location is not None
    user = User(full_name="Simulator Upload User", email="simulator-upload@example.test")
    database.add(user); database.flush()
    account = Account(user_id=user.id, balance=Decimal("20.00"), is_primary=True)
    vehicle = Vehicle(user_id=user.id, plate_number="VAA1234")
    database.add_all([account, vehicle]); database.flush()

    app = FastAPI(); app.include_router(auth_router); app.include_router(webcam_api.router)
    app.dependency_overrides[get_db] = lambda: database
    monkeypatch.setattr(webcam_api, "service", _SuccessfulImageService())
    response = TestClient(app).post(
        f"/api/webcam/images?location_id={location.id}",
        files={"image": ("plate.png", b"image-bytes", "image/png")},
        headers={**admin_auth_headers, "Idempotency-Key": "simulator-upload-0001"},
    )

    detection = database.scalar(select(DetectionRecord).where(DetectionRecord.location_id == location.id))
    transaction = database.scalar(select(TollTransaction).where(TollTransaction.location_id == location.id))
    assert response.status_code == 200, response.text
    assert response.json()["payment_status"] == "successful"
    assert detection is not None and detection.source == "uploaded_image"
    assert transaction is not None and transaction.status == "successful"


def test_singaporean_simulator_upload_returns_separate_charge_components(
    database, admin_auth_headers, monkeypatch
) -> None:
    location = database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))
    user = User(full_name="Synthetic Singapore Upload Driver", email="sg-upload@example.test")
    database.add(user)
    database.flush()
    account = Account(user_id=user.id, balance=Decimal("50.00"), is_primary=True)
    vehicle = Vehicle(user_id=user.id, plate_number="GBC1234R", registration_origin="singaporean")
    database.add_all([account, vehicle])
    database.flush()
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(webcam_api.router)
    app.dependency_overrides[get_db] = lambda: database
    monkeypatch.setattr(webcam_api, "service", _SuccessfulSingaporeanImageService())

    response = TestClient(app).post(
        f"/api/webcam/images?location_id={location.id}",
        files={"image": ("plate.png", b"image-bytes", "image/png")},
        headers={**admin_auth_headers, "Idempotency-Key": "simulator-sg-upload-0001"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["payment_status"] == "successful"
    assert body["plate_origin"] == "singaporean"
    assert Decimal(str(body["payment_foreign_vehicle_charge"])) == Decimal("20.00")
    assert Decimal(str(body["payment_amount"])) == (
        Decimal(str(body["payment_dynamic_toll_amount"])) + Decimal("20.00")
    )
    transaction = database.scalar(select(TollTransaction).where(TollTransaction.location_id == location.id))
    assert transaction.foreign_vehicle_charge == Decimal("20.00")
    assert transaction.amount == Decimal(str(body["payment_amount"]))

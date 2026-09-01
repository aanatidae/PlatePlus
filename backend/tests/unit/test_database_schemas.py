from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.database import (
    AccountCreate,
    DetectionRecordCreate,
    TrafficRecordCreate,
    VehicleCreate,
)


def test_vehicle_plate_is_normalized() -> None:
    vehicle = VehicleCreate(user_id=uuid4(), plate_number="vaa 1234")
    assert vehicle.plate_number == "VAA1234"


def test_account_rejects_negative_balance() -> None:
    with pytest.raises(ValidationError):
        AccountCreate(user_id=uuid4(), balance=Decimal("-0.01"))


def test_traffic_percentage_is_bounded() -> None:
    with pytest.raises(ValidationError):
        TrafficRecordCreate(
            vehicle_count=120,
            road_capacity=100,
            congestion_percentage=Decimal(120),
            congestion_category="severe",
        )


def test_detection_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        DetectionRecordCreate(detection_confidence=Decimal("1.1"), status="accepted")

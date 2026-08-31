from __future__ import annotations

import numpy as np
import pytest

from alpr.plate.crop import extract_plate_crop, select_best_plate_detection
from alpr.plate.normalization import is_plausible_malaysian_plate, normalize_plate_text
from alpr.types import BoundingBox, PlateDetection, recognition_decision


def test_normalize_plate_text_removes_layout_noise() -> None:
    assert normalize_plate_text(" b k v - 1234 ") == "BKV1234"


def test_normalize_plate_text_does_not_guess_ambiguous_characters() -> None:
    assert normalize_plate_text("BO 10") == "BO10"


@pytest.mark.parametrize("value", ["BKV1234", "VAB12", "ABC123X"])
def test_common_malaysian_plate_shapes_are_plausible(value: str) -> None:
    assert is_plausible_malaysian_plate(value)


@pytest.mark.parametrize("value", ["1234", "ABCD1234", "ABC12345"])
def test_invalid_plate_shapes_are_not_plausible(value: str) -> None:
    assert not is_plausible_malaysian_plate(value)


def test_extract_plate_crop_clamps_and_pads_box() -> None:
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    detection = PlateDetection(BoundingBox(0, 2, 40, 22), confidence=0.91)

    crop = extract_plate_crop(image, detection, padding_ratio=0.1)

    assert crop.bounding_box == BoundingBox(0, 0, 44, 24)
    assert crop.image.shape == (24, 44, 3)
    assert crop.detection_confidence == 0.91


def test_select_best_plate_detection_ignores_other_classes() -> None:
    detection = select_best_plate_detection(
        [
            PlateDetection(BoundingBox(1, 1, 2, 2), 0.99, class_name="car"),
            PlateDetection(BoundingBox(3, 3, 6, 6), 0.75),
        ]
    )

    assert detection is not None
    assert detection.confidence == 0.75


def test_low_confidence_cannot_be_accepted_for_charging() -> None:
    assert not recognition_decision(0.49, 0.95, 0.5, 0.7).accepted
    assert not recognition_decision(0.95, 0.69, 0.5, 0.7).accepted
    assert recognition_decision(0.95, 0.85, 0.5, 0.7).accepted
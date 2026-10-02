from __future__ import annotations

import pytest

from alpr.plate.normalization import correct_common_ocr_confusions
from alpr.plate.origin import (
    classify_plate_origin,
    matches_malaysian_pattern,
    matches_singaporean_pattern,
)


@pytest.mark.parametrize("plate", ["BKV1234", "VAB12", "ABC123X", "QAB1234"])
def test_supported_malaysian_patterns(plate: str) -> None:
    assert matches_malaysian_pattern(plate)
    assert classify_plate_origin(plate).origin == "malaysian"


@pytest.mark.parametrize("plate", ["GBC1234R", "YN1234R", "XD1234E"])
def test_supported_singaporean_patterns(plate: str) -> None:
    assert matches_singaporean_pattern(plate)
    assert classify_plate_origin(plate).origin == "singaporean"


def test_overlapping_singapore_car_and_malaysian_shape_is_ambiguous() -> None:
    plate = "SLP1234A"
    assert matches_malaysian_pattern(plate)
    assert matches_singaporean_pattern(plate)
    assert classify_plate_origin(plate).reason == "ambiguous_supported_patterns"
    assert classify_plate_origin(plate).origin == "unknown"


@pytest.mark.parametrize("plate", ["", "1234", "ABCD1234", "GBC1234", "ABC12345"])
def test_unsupported_patterns_remain_unknown(plate: str) -> None:
    assert classify_plate_origin(plate).origin == "unknown"
    assert classify_plate_origin(plate).reason == "unsupported_plate_pattern"


def test_ocr_confusion_never_resolves_an_overlap_to_a_country() -> None:
    corrected = correct_common_ocr_confusions("S0P1234A")
    assert corrected == "SOP1234A"
    assert classify_plate_origin(corrected).origin == "unknown"


def test_ocr_confusion_can_recover_a_supported_singaporean_shape() -> None:
    corrected = correct_common_ocr_confusions("G8C1234R")
    assert corrected == "GBC1234R"
    assert classify_plate_origin(corrected).origin == "singaporean"

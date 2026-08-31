"""Plate crop extraction from detector bounding boxes."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from alpr.types import BoundingBox, PlateCrop, PlateDetection


def select_best_plate_detection(detections: Iterable[PlateDetection]) -> PlateDetection | None:
    """Select the highest-confidence car-plate detection."""
    candidates = [item for item in detections if item.class_name == "car plate"]
    return max(candidates, key=lambda item: item.confidence, default=None)


def extract_plate_crop(
    image: np.ndarray,
    detection: PlateDetection,
    padding_ratio: float = 0.05,
) -> PlateCrop:
    """Crop and clamp a plate region, with a small margin for OCR context."""
    if image.ndim not in (2, 3):
        raise ValueError("image must be a grayscale or colour image array")
    if not 0 <= padding_ratio <= 0.5:
        raise ValueError("padding_ratio must be between 0 and 0.5")

    image_height, image_width = image.shape[:2]
    source = detection.bounding_box
    pad_x = round(source.width() * padding_ratio)
    pad_y = round(source.height() * padding_ratio)
    box = BoundingBox(
        left=max(0, source.left - pad_x),
        top=max(0, source.top - pad_y),
        right=min(image_width, source.right + pad_x),
        bottom=min(image_height, source.bottom + pad_y),
    )
    if box.width() <= 0 or box.height() <= 0:
        raise ValueError("detection box does not overlap the image")

    return PlateCrop(
        image=image[box.top : box.bottom, box.left : box.right].copy(),
        bounding_box=box,
        detection_confidence=detection.confidence,
    )
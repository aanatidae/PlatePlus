"""Local webcam-frame processing through YOLO and PaddleOCR."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from alpr.ocr.paddleocr_recognizer import PaddleOcrPlateRecognizer
from alpr.plate.crop import extract_plate_crop, select_best_plate_detection
from alpr.types import BoundingBox, PlateDetection, recognition_decision


class FrameProcessorError(RuntimeError):
    """A safe, user-facing webcam inference failure."""


@dataclass(frozen=True)
class ProcessedFrame:
    status: str
    message: str
    plate_text: str | None = None
    detection_confidence: float | None = None
    ocr_confidence: float | None = None
    bounding_box: BoundingBox | None = None
    charge_eligible: bool = False


class PlateDetector(Protocol):
    def detect(self, image: np.ndarray) -> list[PlateDetection]: ...


class YoloPlateDetector:
    """Lazy local adapter for the Git-ignored YOLO weights artifact."""

    def __init__(self, model_path: Path, confidence_threshold: float) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._model: object | None = None

    def detect(self, image: np.ndarray) -> list[PlateDetection]:
        model = self._get_model()
        result = model(image, conf=self._confidence_threshold, verbose=False)[0]
        names = result.names
        detections: list[PlateDetection] = []
        for box in result.boxes:
            class_name = str(names[int(box.cls[0])])
            if class_name != "car plate":
                continue
            left, top, right, bottom = (round(float(value)) for value in box.xyxy[0].tolist())
            detections.append(
                PlateDetection(
                    bounding_box=BoundingBox(left, top, right, bottom),
                    confidence=float(box.conf[0]),
                    class_name=class_name,
                )
            )
        return detections

    def _get_model(self):
        if self._model is not None:
            return self._model
        if not self._model_path.is_file():
            raise FrameProcessorError(
                f"YOLO model is unavailable at {self._model_path}. Copy car_plate_yolo_best.pt to this path."
            )
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise FrameProcessorError("YOLO dependencies are not installed for local webcam inference.") from error
        self._model = YOLO(self._model_path)
        return self._model


class WebcamFrameProcessor:
    """Decode one browser-captured JPEG and return safe recognition status."""

    def __init__(
        self,
        detector: PlateDetector,
        recognizer: PaddleOcrPlateRecognizer,
        detection_threshold: float,
        ocr_threshold: float,
    ) -> None:
        self._detector = detector
        self._recognizer = recognizer
        self._detection_threshold = detection_threshold
        self._ocr_threshold = ocr_threshold

    def process(self, frame_bytes: bytes) -> ProcessedFrame:
        image = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise FrameProcessorError("The webcam frame could not be decoded.")

        detection = select_best_plate_detection(self._detector.detect(image))
        if detection is None:
            return ProcessedFrame("no_plate_detected", "No license plate was detected in this frame.")

        crop = extract_plate_crop(image, detection)
        ocr = self._recognizer.recognize(crop.image)
        decision = recognition_decision(
            detection.confidence,
            ocr.confidence,
            self._detection_threshold,
            self._ocr_threshold,
        )
        status = "accepted_for_vehicle_lookup" if decision.accepted else decision.reason or "recognition_rejected"
        return ProcessedFrame(
            status=status,
            message="Recognition passed confidence checks." if decision.accepted else "Recognition did not pass confidence checks.",
            plate_text=ocr.normalized_text or None,
            detection_confidence=detection.confidence,
            ocr_confidence=ocr.confidence,
            bounding_box=crop.bounding_box,
            charge_eligible=decision.accepted,
        )

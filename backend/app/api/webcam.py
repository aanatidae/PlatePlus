"""Local-only HTTP endpoints for browser webcam capture."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.settings import Settings
from app.schemas.webcam import WebcamBoundingBox, WebcamFrameResult
from app.services.detection.webcam_processor import FrameProcessorError, WebcamFrameProcessor, YoloPlateDetector
from app.services.detection.webcam_service import WebcamService
from alpr.ocr.paddleocr_recognizer import PaddleOcrPlateRecognizer

router = APIRouter(prefix="/api/webcam", tags=["webcam"])
settings = Settings()
service = WebcamService(
    WebcamFrameProcessor(
        YoloPlateDetector(settings.yolo_model_path, settings.detection_confidence_threshold),
        PaddleOcrPlateRecognizer(settings.paddleocr_model_storage),
        settings.detection_confidence_threshold,
        settings.ocr_confidence_threshold,
    ),
    settings.webcam_duplicate_cooldown_seconds,
)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def start_session() -> dict[str, object]:
    session_id = str(uuid4())
    service.start_session(session_id)
    return {"session_id": session_id, "frame_interval_ms": settings.webcam_frame_interval_ms}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def stop_session(session_id: str) -> None:
    service.stop_session(session_id)


@router.post("/sessions/{session_id}/frames", response_model=WebcamFrameResult)
async def process_frame(session_id: str, frame: UploadFile = File(...)) -> WebcamFrameResult:
    if frame.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Webcam frames must be JPEG, PNG, or WebP images.")
    frame_bytes = await frame.read(settings.webcam_max_frame_bytes + 1)
    if len(frame_bytes) > settings.webcam_max_frame_bytes:
        raise HTTPException(status_code=413, detail="Webcam frame exceeds the local size limit.")
    try:
        result = service.process_frame(session_id, frame_bytes)
    except FrameProcessorError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    box = result.bounding_box
    return WebcamFrameResult(
        status=result.status,
        message=result.message,
        plate_text=result.plate_text,
        detection_confidence=result.detection_confidence,
        ocr_confidence=result.ocr_confidence,
        bounding_box=WebcamBoundingBox(**box.__dict__) if box else None,
        charge_eligible=result.charge_eligible,
    )

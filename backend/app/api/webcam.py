"""Local-only HTTP endpoints for browser webcam capture."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from alpr.ocr.paddleocr_recognizer import PaddleOcrPlateRecognizer
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.db.session import get_db
from app.schemas.webcam import WebcamBoundingBox, WebcamFrameResult
from app.services.detection.webcam_processor import (
    FrameProcessorError,
    WebcamFrameProcessor,
    YoloPlateDetector,
)
from app.services.detection.webcam_service import WebcamService
from app.services.transactions.toll_payment import process_toll_event

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
async def process_frame(
    session_id: str,
    frame: Annotated[UploadFile, File()],
    database: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> WebcamFrameResult:
    if frame.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=415, detail="Webcam frames must be JPEG, PNG, or WebP images."
        )
    frame_bytes = await frame.read(settings.webcam_max_frame_bytes + 1)
    if len(frame_bytes) > settings.webcam_max_frame_bytes:
        raise HTTPException(status_code=413, detail="Webcam frame exceeds the local size limit.")
    try:
        result = service.process_frame(session_id, frame_bytes)
    except FrameProcessorError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    payment = None
    if result.plate_text and not result.status.startswith("duplicate_plate"):
        payment = process_toll_event(
            database,
            idempotency_key=idempotency_key or f"webcam:{session_id}:{uuid4()}",
            raw_plate_text=result.plate_text,
            normalized_plate=result.plate_text,
            detection_confidence=result.detection_confidence,
            ocr_confidence=result.ocr_confidence,
            recognition_accepted=result.charge_eligible,
        )
    box = result.bounding_box
    return WebcamFrameResult(
        status=result.status,
        message=result.message,
        plate_text=result.plate_text,
        detection_confidence=result.detection_confidence,
        ocr_confidence=result.ocr_confidence,
        bounding_box=WebcamBoundingBox(**box.__dict__) if box else None,
        charge_eligible=result.charge_eligible,
        payment_status=payment.status if payment else None,
        payment_amount=float(payment.amount) if payment else None,
        payment_balance_after=float(payment.balance_after) if payment and payment.balance_after is not None else None,
        payment_duplicate=payment.duplicate if payment else False,
    )

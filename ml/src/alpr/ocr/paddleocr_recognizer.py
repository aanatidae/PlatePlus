"""Lazy PaddleOCR 3.x adapter for licence-plate recognition."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from alpr.plate.normalization import is_plausible_malaysian_plate, normalize_plate_text
from alpr.types import OcrResult


class PaddleOcrPlateRecognizer:
    """Recognize one plate crop with PaddleOCR's CPU inference pipeline."""

    def __init__(self, model_storage_directory: str | Path | None = None) -> None:
        self._model_storage_directory = (
            str(model_storage_directory) if model_storage_directory is not None else None
        )
        self._ocr: Any | None = None

    def recognize(self, crop: np.ndarray) -> OcrResult:
        if crop.size == 0:
            raise ValueError("cannot run OCR on an empty plate crop")

        result = next(iter(self._get_ocr().predict(crop))).json["res"]
        candidates = [
            (str(text), float(score))
            for text, score in zip(result["rec_texts"], result["rec_scores"], strict=True)
        ]
        if not candidates:
            return OcrResult(raw_text="", normalized_text="", confidence=0.0)

        plausible = [item for item in candidates if is_plausible_malaysian_plate(item[0])]
        raw_text, confidence = max(plausible or candidates, key=lambda item: item[1])
        return OcrResult(
            raw_text=raw_text,
            normalized_text=normalize_plate_text(raw_text),
            confidence=confidence,
        )

    def _get_ocr(self) -> Any:
        if self._ocr is not None:
            return self._ocr

        # PaddleOCR imports ModelScope, which imports Torch. Loading Torch first
        # avoids a Windows DLL load-order conflict when YOLO and Paddle coexist.
        import torch  # noqa: F401

        if self._model_storage_directory:
            os.environ.setdefault("PADDLE_PDX_CACHE_HOME", self._model_storage_directory)
        try:
            from paddleocr import PaddleOCR
        except ImportError as error:
            raise RuntimeError(
                "PaddleOCR is not installed. Install the ML PaddleOCR extra before running recognition."
            ) from error

        self._ocr = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        return self._ocr

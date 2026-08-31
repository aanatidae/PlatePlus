"""Lazy EasyOCR adapter for licence-plate recognition."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from alpr.plate.normalization import normalize_plate_text
from alpr.types import OcrResult


class EasyOcrPlateRecognizer:
    """Recognize one plate crop while keeping EasyOCR optional at import time."""

    def __init__(self, model_storage_directory: str | Path | None = None) -> None:
        self._model_storage_directory = (
            str(model_storage_directory) if model_storage_directory is not None else None
        )
        self._reader: Any | None = None

    def recognize(self, crop: np.ndarray) -> OcrResult:
        if crop.size == 0:
            raise ValueError("cannot run OCR on an empty plate crop")

        reader = self._get_reader()
        candidates = reader.readtext(
            crop,
            detail=1,
            paragraph=False,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        )
        if not candidates:
            return OcrResult(raw_text="", normalized_text="", confidence=0.0)

        _box, raw_text, confidence = max(candidates, key=lambda item: float(item[2]))
        return OcrResult(
            raw_text=str(raw_text),
            normalized_text=normalize_plate_text(str(raw_text)),
            confidence=float(confidence),
        )

    def _get_reader(self) -> Any:
        if self._reader is not None:
            return self._reader
        try:
            import easyocr
        except ImportError as error:
            raise RuntimeError(
                "EasyOCR is not installed. Install the ML OCR extra before running recognition."
            ) from error

        options: dict[str, Any] = {"lang_list": ["en"], "gpu": False}
        if self._model_storage_directory:
            options["model_storage_directory"] = self._model_storage_directory
        self._reader = easyocr.Reader(**options)
        return self._reader
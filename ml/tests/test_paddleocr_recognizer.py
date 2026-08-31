from __future__ import annotations

import numpy as np

from alpr.ocr.paddleocr_recognizer import PaddleOcrPlateRecognizer


class _FakeResult:
    def __init__(self) -> None:
        self.json = {
            "res": {
                "rec_texts": ["Auto Selection", "TBU 5553"],
                "rec_scores": [0.999, 0.9],
            }
        }


class _FakeOcr:
    def predict(self, crop: np.ndarray):
        return iter([_FakeResult()])


def test_paddle_recognizer_prefers_a_plausible_plate_candidate() -> None:
    recognizer = PaddleOcrPlateRecognizer()
    recognizer._ocr = _FakeOcr()

    result = recognizer.recognize(np.zeros((24, 80, 3), dtype=np.uint8))

    assert result.normalized_text == "TBU5553"
    assert result.confidence == 0.9

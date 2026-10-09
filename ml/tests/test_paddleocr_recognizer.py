from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

from alpr.ocr.paddleocr_recognizer import PaddleOcrPlateRecognizer


class _FakeResult:
    def __init__(self, plate: str = "TBU 5553") -> None:
        self.json = {
            "res": {
                "rec_texts": ["Auto Selection", plate],
                "rec_scores": [0.999, 0.9],
            }
        }


class _FakeOcr:
    def __init__(self, plate: str = "TBU 5553") -> None:
        self.plate = plate

    def predict(self, crop: np.ndarray):
        return iter([_FakeResult(self.plate)])


def test_paddle_recognizer_prefers_a_plausible_plate_candidate() -> None:
    recognizer = PaddleOcrPlateRecognizer()
    recognizer._ocr = _FakeOcr()

    result = recognizer.recognize(np.zeros((24, 80, 3), dtype=np.uint8))

    assert result.normalized_text == "TBU5553"
    assert result.confidence == 0.9


def test_paddle_recognizer_prefers_a_singaporean_pattern_candidate() -> None:
    recognizer = PaddleOcrPlateRecognizer()
    recognizer._ocr = _FakeOcr("GBC 1234 R")

    result = recognizer.recognize(np.zeros((24, 80, 3), dtype=np.uint8))

    assert result.normalized_text == "GBC1234R"
    assert result.raw_text == "GBC 1234 R"


def test_windows_paddle_dll_paths_are_retained_and_constructor_errors_are_wrapped(
    monkeypatch, tmp_path
) -> None:
    import alpr.ocr.paddleocr_recognizer as adapter

    for name in ("libs", "base"):
        (tmp_path / name).mkdir()
    handles = []

    def register(directory):
        handle = SimpleNamespace(directory=directory)
        handles.append(handle)
        return handle

    def broken_constructor(**kwargs):
        raise ImportError("DLL load failed while importing libpaddle")

    monkeypatch.setattr(adapter.sys, "platform", "win32")
    monkeypatch.setattr(adapter, "find_spec", lambda name: SimpleNamespace(
        submodule_search_locations=[str(tmp_path)]
    ))
    monkeypatch.setattr(adapter.os, "add_dll_directory", register, raising=False)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "paddle", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "paddleocr", SimpleNamespace(PaddleOCR=broken_constructor))
    recognizer = PaddleOcrPlateRecognizer()
    for _ in range(2):
        with pytest.raises(RuntimeError, match="could not load its Paddle runtime") as error:
            recognizer._get_ocr()
        assert isinstance(error.value.__cause__, ImportError)
    assert recognizer._dll_directories == handles
    assert [h.directory for h in handles] == [str(tmp_path / "libs"), str(tmp_path / "base")]
    assert recognizer._ocr is None

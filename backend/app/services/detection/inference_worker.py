"""One disposable local inference process, independent of the API event loop."""

from __future__ import annotations

import multiprocessing
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic

from app.services.detection.webcam_processor import FrameProcessorError, ProcessedFrame


@dataclass(frozen=True)
class InferenceConfig:
    model_path: Path
    ocr_storage: Path
    detection_threshold: float
    ocr_threshold: float


def _serve_inference(connection, config: InferenceConfig) -> None:
    # Models are lazy and cached here. This process never imports a database
    # session, invokes Gemini, writes images or processes a payment.
    from alpr.ocr.paddleocr_recognizer import PaddleOcrPlateRecognizer

    from app.services.detection.webcam_processor import WebcamFrameProcessor, YoloPlateDetector

    processor = WebcamFrameProcessor(
        YoloPlateDetector(config.model_path, config.detection_threshold),
        PaddleOcrPlateRecognizer(config.ocr_storage),
        config.detection_threshold,
        config.ocr_threshold,
    )
    try:
        connection.send(("ready", None))
        while True:
            image_bytes = connection.recv()
            try:
                result = processor.process(image_bytes)
            except FrameProcessorError as error:
                connection.send(("error", str(error)))
            else:
                connection.send(("result", result))
            finally:
                del image_bytes
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


class IsolatedFrameProcessor:
    """Serialize scans, bound native hangs and restart only our own worker.

    Call ``process`` from a thread, never the API's asyncio event loop. A timeout
    terminates the native process, so no orphan scan can later authorize payment.
    """

    def __init__(self, config: InferenceConfig, timeout_seconds: float = 60) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self._context = multiprocessing.get_context("spawn")
        self._target = _serve_inference
        self._lock = Lock()
        self._process = None
        self._connection = None

    def _discard(self) -> None:
        process, self._process = self._process, None
        connection, self._connection = self._connection, None
        if process is not None:
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=2)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=2)
            process.close()
        if connection is not None:
            connection.close()

    def _receive(self, deadline: float):
        if not self._connection.poll(max(0, deadline - monotonic())):
            self._discard()
            raise FrameProcessorError(
                f"Local plate processing timed out after {self.timeout_seconds:g} seconds. "
                "Retry this image; no simulated payment was made."
            )
        return self._connection.recv()

    def process(self, image_bytes: bytes) -> ProcessedFrame:
        if not self._lock.acquire(blocking=False):
            raise FrameProcessorError(
                "Another local plate scan is still running. Wait for it to finish, then retry."
            )
        try:
            deadline = monotonic() + self.timeout_seconds
            if self._process is None or not self._process.is_alive():
                self._discard()
                self._connection, child = self._context.Pipe()
                self._process = self._context.Process(
                    target=self._target, args=(child, self.config), daemon=True,
                    name="plateplus-local-inference",
                )
                try:
                    self._process.start()
                finally:
                    child.close()
                # Wait for startup before sending a bounded image. The child is
                # then waiting on recv, rather than stuck importing native code.
                if self._receive(deadline)[0] != "ready":
                    raise EOFError("Inference worker startup failed.")
            self._connection.send(image_bytes)
            kind, value = self._receive(deadline)
            if kind == "error":
                raise FrameProcessorError(value)
            if kind != "result" or not isinstance(value, ProcessedFrame):
                raise EOFError("Invalid local inference response.")
            return value
        except (EOFError, OSError) as error:
            self._discard()
            raise FrameProcessorError(
                "The local plate worker stopped unexpectedly. Retry this image; "
                "no simulated payment was made."
            ) from error
        finally:
            self._lock.release()

    def close(self) -> None:
        with self._lock:
            self._discard()

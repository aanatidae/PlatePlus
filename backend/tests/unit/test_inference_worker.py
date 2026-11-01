"""Exercise actual child-process timeout/recovery without native ML or images."""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import monotonic, sleep

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import webcam
from app.api.auth import require_admin
from app.db.session import get_db
from app.services.detection.inference_worker import InferenceConfig, IsolatedFrameProcessor
from app.services.detection.webcam_processor import FrameProcessorError, ProcessedFrame


def fake_worker(connection, config):
    connection.send(("ready", None))
    try:
        while True:
            value = connection.recv()
            if value == b"hang":
                sleep(30)
            elif value == b"crash":
                os._exit(7)
            elif value == b"error":
                connection.send(("error", "Unread local image."))
                continue
            connection.send(("result", ProcessedFrame("no_plate_detected", str(os.getpid()))))
    except EOFError:
        pass
    finally:
        connection.close()


@pytest.fixture
def worker():
    processor = IsolatedFrameProcessor(InferenceConfig(Path("unused"), Path("unused"), .5, .7), 10)
    processor._target = fake_worker
    yield processor
    processor.close()


def test_worker_reuses_native_process_for_warm_scans_and_clears_it_on_close(worker):
    first = worker.process(b"scan")
    assert worker.process(b"scan").message == first.message
    child = worker._process
    worker.close()
    assert worker._process is None and worker._connection is None
    assert child._closed


def test_native_hang_is_terminated_and_next_scan_starts_a_fresh_process(worker):
    first_pid = worker.process(b"scan").message
    worker.timeout_seconds = .3
    start = monotonic()
    with pytest.raises(FrameProcessorError, match="timed out.*no simulated payment"):
        worker.process(b"hang")
    assert monotonic() - start < 8
    assert worker._process is None
    worker.timeout_seconds = 10
    assert worker.process(b"scan").message != first_pid


def test_worker_crash_is_safe_and_recoverable(worker):
    worker.process(b"scan")
    with pytest.raises(FrameProcessorError, match="stopped unexpectedly"):
        worker.process(b"crash")
    assert worker.process(b"scan").status == "no_plate_detected"


def test_parallel_scan_is_rejected_instead_of_queuing_more_native_work(worker):
    worker.process(b"scan")
    worker.timeout_seconds = .3
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(worker.process, b"hang")
        for _ in range(100):
            if worker._lock.locked():
                break
            sleep(.01)
        with pytest.raises(FrameProcessorError, match="Another local plate scan"):
            worker.process(b"scan")
        with pytest.raises(FrameProcessorError, match="timed out"):
            pending.result(timeout=8)


def test_safe_inference_error_does_not_discard_healthy_cached_worker(worker):
    pid = worker.process(b"scan").message
    with pytest.raises(FrameProcessorError, match="Unread local image"):
        worker.process(b"error")
    assert worker.process(b"scan").message == pid


@pytest.mark.parametrize("source", ["image", "frame"])
def test_slow_scan_does_not_block_health_or_reach_fallback_or_payment(monkeypatch, source):
    entered, release = Event(), Event()

    class SlowService:
        def process_image(self, *_):
            entered.set()
            assert release.wait(timeout=5)
            raise FrameProcessorError("Timed out; no simulated payment was made.")

        process_frame = process_image

    def forbidden(*args, **kwargs):
        pytest.fail("Timed-out inference must not reach fallback, pricing or payment.")

    monkeypatch.setattr(webcam, "service", SlowService())
    monkeypatch.setattr(webcam, "fallback", type("Fallback", (), {"resolve": forbidden})())
    monkeypatch.setattr(webcam, "process_toll_event", forbidden)
    monkeypatch.setattr(webcam, "prepare_webcam_crossing_price", forbidden)
    app = FastAPI()
    app.include_router(webcam.router)
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[get_db] = lambda: None

    @app.get("/health")
    async def health():
        await asyncio.sleep(0)
        return {"status": "ok"}

    with TestClient(app) as client, ThreadPoolExecutor() as pool:
        path = "/api/webcam/images" if source == "image" else "/api/webcam/sessions/test/frames"
        pending = pool.submit(client.post, path, files={source: ("synthetic.png", b"synthetic", "image/png")})
        assert entered.wait(timeout=3)
        try:
            start = monotonic()
            assert pool.submit(client.get, "/health").result(timeout=1).json() == {"status": "ok"}
            assert monotonic() - start < 1
        finally:
            release.set()
        assert pending.result(timeout=3).status_code == 503

from decimal import Decimal
from threading import Event
from types import SimpleNamespace

from app.models import TollLocation
from app.services.demo_feed import DemoFeed


class VirtualStop:
    def __init__(self, ticks=1000):
        self.time = 0.0
        self.ticks = ticks
        self.waits = []

    def wait(self, seconds):
        self.waits.append(seconds)
        self.time += max(10, seconds)
        self.ticks -= 1
        return self.is_set()

    def is_set(self):
        return self.ticks <= 0


def setup_feed(monkeypatch, stop):
    locations = [
        SimpleNamespace(id=code, code=code, status="operational")
        for code in ["LDP", "AKLEH", "NPE", "GRAND_SAGA", "SIMULATOR"]
    ]
    vehicles = [SimpleNamespace(plate_number=f"VAA{1000 + i}") for i in range(96)]
    closed = []

    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            closed.append(True)

        def scalars(self, statement):
            return (
                locations
                if statement.column_descriptions[0]["entity"] is TollLocation
                else vehicles
            )

    calls = []
    monkeypatch.setattr(
        "app.api.locations._state",
        lambda *args: {"telemetry": {"congestion_percentage": Decimal(90)}},
    )
    monkeypatch.setattr(
        "app.services.demo_feed.generate_crossing",
        lambda db, location, telemetry, vehicle: calls.append(
            (location.code, vehicle.plate_number)
        ),
    )
    feed = DemoFeed(session_factory=Database, clock=lambda: stop.time)
    return feed, calls, closed


def test_feed_continues_for_hours_and_thousands_of_events_without_record_limit(monkeypatch):
    stop = VirtualStop()
    feed, calls, closed = setup_feed(monkeypatch, stop)
    feed._run(stop)
    assert stop.time >= 10_000  # Almost three virtual hours, beyond token expiry.
    assert len(calls) == 3996
    assert len(closed) == 999
    assert {location for location, _ in calls} == {"LDP", "AKLEH", "NPE", "GRAND_SAGA"}
    assert len({plate for _, plate in calls}) == 96
    assert feed.status()["generated_count"] == len(calls)
    assert feed.status()["state"] == "paused"


def test_query_or_telemetry_exception_cannot_kill_worker_and_retries_back_off(monkeypatch, caplog):
    stop = VirtualStop(ticks=10)
    feed, calls, _ = setup_feed(monkeypatch, stop)
    original_tick = feed._tick
    attempts = 0
    observed = []

    def faulty_tick(event):
        nonlocal attempts
        observed.append(feed.status())
        attempts += 1
        if attempts <= 3:
            raise ConnectionError("database connection interrupted before crossing try block")
        original_tick(event)

    monkeypatch.setattr(feed, "_tick", faulty_tick)
    feed._run(stop)
    assert stop.waits[:5] == [0.35, 5, 10, 20, 0.35]
    assert observed[3]["state"] == "recovering"
    assert "ConnectionError" in observed[3]["last_error"]
    assert observed[4]["last_error"] is None
    assert len(calls) > 0
    assert "retrying with backoff" in caplog.text


def test_pause_waits_for_worker_and_restart_has_a_new_stop_event(monkeypatch):
    entered = Event()
    feed = DemoFeed()

    def tick(stop):
        entered.set()

    monkeypatch.setattr(feed, "_tick", tick)
    assert feed.start()
    first_stop = feed._stop
    assert entered.wait(2)
    assert feed.running
    assert not feed.start()
    assert feed.pause()
    assert not feed.worker_alive
    assert not feed.running
    assert feed.start()
    assert feed._stop is not first_stop
    assert first_stop.is_set()
    feed.pause()


def test_pause_during_failed_cycle_interrupts_backoff(monkeypatch):
    failed = Event()
    feed = DemoFeed()

    def tick(stop):
        failed.set()
        raise RuntimeError("recoverable cycle failure")

    monkeypatch.setattr(feed, "_tick", tick)
    feed.start()
    assert failed.wait(2)
    feed.pause()
    assert not feed.worker_alive

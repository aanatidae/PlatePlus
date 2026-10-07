"""Local-only, congestion-paced synthetic crossing feed for capstone demos."""

from __future__ import annotations

import logging
from collections import deque
from datetime import UTC, datetime
from decimal import Decimal
from random import Random
from threading import Event, Lock, Thread
from time import monotonic
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    DetectionRecord,
    PaymentNotification,
    TollLocation,
    TollPrice,
    TollTransaction,
    Vehicle,
    WalletLedgerEntry,
)
from app.services.traffic.webcam_crossings import is_webcam_toll
from app.services.transactions.toll_payment import process_toll_event

DEMO_SOURCE = "demo_generated"
DEMO_KEY_PREFIX = "demo-feed:"


def crossing_interval_seconds(congestion: Decimal | float, *, jitter: float = 0.0) -> float:
    """Map existing congestion to a bounded, presentation-readable crossing cadence."""
    value = max(0.0, min(100.0, float(congestion)))
    if value <= 20:
        base = 10.0
    elif value <= 40:
        base = 6.5
    elif value <= 60:
        base = 4.0
    elif value <= 80:
        base = 2.25
    else:
        base = 1.15
    return max(0.8, base + jitter)


def _latest_or_current_price(
    database: Session, location: TollLocation, amount: Decimal, category: str, now: datetime
) -> None:
    """Keep an existing authoritative price; initialize only when none is persisted."""
    latest = database.scalar(
        select(TollPrice)
        .where(TollPrice.location_id == location.id)
        .order_by(TollPrice.effective_at.desc())
    )
    # Persisted prices are authoritative. A telemetry snapshot taken before a policy
    # update must never overwrite the price committed by that update.
    if latest is not None:
        return
    database.add(
        TollPrice(
            location_id=location.id,
            effective_at=now,
            amount=amount,
            congestion_category=category,
            rule_version="demo-feed",
        )
    )
    database.commit()


def select_demo_vehicle(
    vehicles: list[Vehicle], recent_plates: set[str], random: Random
) -> Vehicle:
    """Choose broadly from the fleet while suppressing short-term plate repeats."""
    eligible = [vehicle for vehicle in vehicles if vehicle.plate_number not in recent_plates]
    return random.choice(eligible or vehicles)


def generate_crossing(
    database: Session, location: TollLocation, telemetry: dict, *, vehicle: Vehicle
) -> str:
    """Create one transparently synthetic detection and its normal simulated payment outcome."""
    if location.status == "retired":
        raise ValueError("Retired toll locations cannot receive demo crossings.")
    if is_webcam_toll(location):
        raise ValueError("Simulator Toll Plaza is webcam-only and cannot receive demo crossings.")
    now = datetime.now(UTC)
    _latest_or_current_price(
        database,
        location,
        Decimal(str(telemetry["current_toll_price"])),
        telemetry["congestion_category"],
        now,
    )
    outcome = process_toll_event(
        database,
        idempotency_key=f"{DEMO_KEY_PREFIX}{location.id}:{uuid4()}",
        raw_plate_text=vehicle.plate_number,
        normalized_plate=vehicle.plate_number,
        detection_confidence=0.99,
        ocr_confidence=0.99,
        recognition_accepted=True,
        source=DEMO_SOURCE,
        detected_at=now,
        location_id=location.id,
    )
    return outcome.status


def reset_demo_activity(database: Session) -> dict[str, int]:
    """Remove only feed-created records and reverse their successful synthetic deductions."""
    transactions = list(
        database.scalars(
            select(TollTransaction).where(
                TollTransaction.idempotency_key.like(f"{DEMO_KEY_PREFIX}%")
            )
        )
    )
    transaction_ids = [row.id for row in transactions]
    for row in transactions:
        if row.status == "successful" and row.account is not None and row.reversed_at is None:
            row.account.balance += row.amount
    if transaction_ids:
        database.execute(
            delete(WalletLedgerEntry).where(WalletLedgerEntry.transaction_id.in_(transaction_ids))
        )
        database.execute(
            delete(PaymentNotification).where(
                PaymentNotification.transaction_id.in_(transaction_ids)
            )
        )
        database.execute(delete(TollTransaction).where(TollTransaction.id.in_(transaction_ids)))
    detections = database.execute(
        delete(DetectionRecord).where(DetectionRecord.source == DEMO_SOURCE)
    )
    database.commit()
    return {
        "transactions_removed": len(transactions),
        "detections_removed": int(detections.rowcount or 0),
    }


class DemoFeed:
    """A singleton worker with explicit lifecycle and bounded recovery backoff."""

    def __init__(self, *, session_factory=None, clock=monotonic) -> None:
        self._lock = Lock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._session_factory = session_factory or SessionLocal
        self._clock = clock
        self._next_due: dict[str, float] = {}
        self._random = Random(20260909)
        self._recent_by_location: dict[str, deque[str]] = {}
        self._recent_global: deque[str] = deque(maxlen=4)
        self._state = "paused"
        self._last_error: str | None = None
        self._last_success_at: str | None = None
        self._generated_count = 0
        self._consecutive_errors = 0

    @property
    def worker_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def running(self) -> bool:
        return self.worker_alive and not self._stop.is_set()

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self.running,
                "state": self._state,
                "last_error": self._last_error,
                "last_success_at": self._last_success_at,
                "generated_count": self._generated_count,
                "consecutive_errors": self._consecutive_errors,
            }

    def start(self) -> bool:
        with self._lock:
            # Never clear an old worker's stop event or start a second worker.
            if self.worker_alive:
                return False
            self._stop = Event()
            self._state = "running"
            self._last_error = None
            self._consecutive_errors = 0
            self._thread = Thread(
                target=self._run, args=(self._stop,), name="plateplus-demo-feed", daemon=True
            )
            self._thread.start()
            return True

    def pause(self) -> bool:
        with self._lock:
            requested = self.running
            self._stop.set()
            worker = self._thread
            self._state = "stopping" if self.worker_alive else "paused"
        if worker:
            worker.join(timeout=10)
        return requested

    def _tick(self, stop: Event) -> None:
        from app.api.locations import _state

        with self._session_factory() as database:
            locations = list(
                database.scalars(select(TollLocation).where(TollLocation.status == "operational"))
            )
            vehicles = list(
                database.scalars(
                    select(Vehicle)
                    .where(Vehicle.is_active.is_(True), Vehicle.registration_origin == "malaysian")
                    .order_by(Vehicle.plate_number)
                )
            )
            if not vehicles:
                raise RuntimeError("No active synthetic Malaysian presentation vehicles")
            for location in locations:
                if stop.is_set():
                    return
                if is_webcam_toll(location):
                    continue
                now_tick = self._clock()
                key = str(location.id)
                if now_tick < self._next_due.get(key, 0):
                    continue
                telemetry = _state(database, location).get("telemetry")
                if not telemetry:
                    continue
                recent = self._recent_by_location.setdefault(key, deque(maxlen=16))
                vehicle = select_demo_vehicle(
                    vehicles, set(recent) | set(self._recent_global), self._random
                )
                # Session context closes/rolls back on error; recovery uses a fresh session.
                generate_crossing(database, location, telemetry, vehicle=vehicle)
                recent.append(vehicle.plate_number)
                self._recent_global.append(vehicle.plate_number)
                jitter = self._random.uniform(-0.18, 0.18) * crossing_interval_seconds(
                    telemetry["congestion_percentage"]
                )
                self._next_due[key] = now_tick + crossing_interval_seconds(
                    telemetry["congestion_percentage"], jitter=jitter
                )
                with self._lock:
                    self._generated_count += 1
                    self._last_success_at = datetime.now(UTC).isoformat()

    def _run(self, stop: Event) -> None:
        logger = logging.getLogger(__name__)
        delay = 0.35
        try:
            while not stop.wait(delay):
                try:
                    self._tick(stop)
                    with self._lock:
                        recovered = self._consecutive_errors > 0
                        self._consecutive_errors = 0
                        self._last_error = None
                        self._state = "running"
                    if recovered:
                        logger.info("PlatePlus presentation feed recovered")
                    delay = 0.35
                except Exception as error:
                    logger.exception(
                        "PlatePlus presentation feed cycle failed; retrying with backoff"
                    )
                    with self._lock:
                        self._consecutive_errors += 1
                        self._state = "recovering"
                        self._last_error = f"Feed cycle failed ({type(error).__name__}); retrying automatically. Check backend logs."
                        delay = min(30.0, 5.0 * 2 ** min(self._consecutive_errors - 1, 3))
        finally:
            with self._lock:
                self._state = "paused" if stop.is_set() else "error"


demo_feed = DemoFeed()

"""Local-only, congestion-paced synthetic crossing feed for capstone demos."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from random import Random
from threading import Event, Lock, Thread
from time import monotonic
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import DetectionRecord, PaymentNotification, TollLocation, TollPrice, TollTransaction, Vehicle, WalletLedgerEntry
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


def _latest_or_current_price(database: Session, location: TollLocation, amount: Decimal, category: str, now: datetime) -> None:
    """Ensure the payment workflow has a price matching the already-calculated live state."""
    latest = database.scalar(select(TollPrice).where(TollPrice.location_id == location.id).order_by(TollPrice.effective_at.desc()))
    if latest and latest.amount == amount and latest.congestion_category == category:
        return
    database.add(TollPrice(location_id=location.id, effective_at=now, amount=amount, congestion_category=category, rule_version="demo-feed"))
    database.commit()


def generate_crossing(database: Session, location: TollLocation, telemetry: dict, *, ordinal: int) -> str:
    """Create one transparently synthetic detection and its normal simulated payment outcome."""
    if is_webcam_toll(location):
        raise ValueError("Simulator Toll Plaza is webcam-only and cannot receive demo crossings.")
    vehicles = list(database.scalars(select(Vehicle).where(Vehicle.is_active.is_(True)).order_by(Vehicle.plate_number)))
    if not vehicles:
        raise ValueError("Synthetic demo vehicles must be seeded before starting the live feed.")
    vehicle = vehicles[ordinal % len(vehicles)]
    now = datetime.now(UTC)
    _latest_or_current_price(database, location, Decimal(str(telemetry["current_toll_price"])), telemetry["congestion_category"], now)
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
    transactions = list(database.scalars(select(TollTransaction).where(TollTransaction.idempotency_key.like(f"{DEMO_KEY_PREFIX}%"))))
    transaction_ids = [row.id for row in transactions]
    for row in transactions:
        if row.status == "successful" and row.account is not None and row.reversed_at is None:
            row.account.balance += row.amount
    if transaction_ids:
        database.execute(delete(WalletLedgerEntry).where(WalletLedgerEntry.transaction_id.in_(transaction_ids)))
        database.execute(delete(PaymentNotification).where(PaymentNotification.transaction_id.in_(transaction_ids)))
        database.execute(delete(TollTransaction).where(TollTransaction.id.in_(transaction_ids)))
    detections = database.execute(delete(DetectionRecord).where(DetectionRecord.source == DEMO_SOURCE))
    database.commit()
    return {"transactions_removed": len(transactions), "detections_removed": int(detections.rowcount or 0)}


class DemoFeed:
    """One process-local worker. It is intentionally available only to the local backend."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._ordinal = 0
        self._next_due: dict[str, float] = {}
        self._random = Random(20260909)

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop.is_set())

    def start(self) -> bool:
        with self._lock:
            if self.running:
                return False
            self._stop.clear()
            self._thread = Thread(target=self._run, name="plateplus-demo-feed", daemon=True)
            self._thread.start()
            return True

    def pause(self) -> bool:
        with self._lock:
            if not self.running:
                return False
            self._stop.set()
            return True

    def _run(self) -> None:
        while not self._stop.wait(0.35):
            now_tick = monotonic()
            with SessionLocal() as database:
                from app.api.locations import _state
                locations = list(database.scalars(select(TollLocation).where(TollLocation.status == "operational")))
                for location in locations:
                    if is_webcam_toll(location):
                        continue
                    key = str(location.id)
                    if now_tick < self._next_due.get(key, 0):
                        continue
                    state = _state(database, location)
                    telemetry = state.get("telemetry")
                    if not telemetry:
                        continue
                    try:
                        generate_crossing(database, location, telemetry, ordinal=self._ordinal)
                        self._ordinal += 1
                    except Exception:
                        database.rollback()
                    jitter = self._random.uniform(-0.18, 0.18) * crossing_interval_seconds(telemetry["congestion_percentage"])
                    self._next_due[key] = now_tick + crossing_interval_seconds(telemetry["congestion_percentage"], jitter=jitter)


demo_feed = DemoFeed()

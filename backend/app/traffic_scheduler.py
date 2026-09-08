"""Standalone scheduler process for persisted simulated traffic configuration.

Run with ``python -m app.traffic_scheduler`` beside the FastAPI API process.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import TrafficRecord, TrafficSimulationSettings
from app.services.traffic.simulation import run_network_simulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_due_simulation() -> bool:
    """Run once if enabled and no scheduled run exists within the selected interval."""
    with SessionLocal.begin() as database:
        settings = database.scalar(
            select(TrafficSimulationSettings).where(
                TrafficSimulationSettings.singleton_key == "default"
            )
        )
        if settings is None or not settings.is_enabled:
            return False
        latest = database.scalar(
            select(TrafficRecord)
            .where(TrafficRecord.source == "scheduled")
            .order_by(TrafficRecord.measured_at.desc())
        )
        now = datetime.now(UTC)
        if latest is not None and latest.measured_at > now - timedelta(minutes=settings.interval_minutes):
            return False
        results = run_network_simulation(database, settings, source="scheduled", now=now)
        logger.info("Created scheduled traffic simulations for %s toll locations.", len(results))
        return True


def main() -> None:
    logger.info("Traffic scheduler started.")
    while True:
        try:
            run_due_simulation()
        except Exception:  # pragma: no cover - process resiliency boundary
            logger.exception("Traffic scheduler run failed; it will retry shortly.")
        time.sleep(10)


if __name__ == "__main__":
    main()

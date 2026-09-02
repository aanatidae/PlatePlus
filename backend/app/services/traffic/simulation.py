"""Deterministic-friendly traffic simulation and Malaysia-time profile selection."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DynamicPricingRule, TollPrice, TrafficRecord, TrafficSimulationSettings

MALAYSIA_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")
SCENARIO_CATEGORIES = {
    "normal": "low",
    "moderate": "moderate",
    "peak_hour": "high",
    "severe": "severe",
}
TIME_PROFILE = {
    0: "normal", 1: "normal", 2: "normal", 3: "normal", 4: "normal",
    5: "moderate", 6: "peak_hour", 7: "severe", 8: "severe", 9: "peak_hour",
    10: "moderate", 11: "moderate", 12: "moderate", 13: "moderate", 14: "moderate",
    15: "moderate", 16: "peak_hour", 17: "severe", 18: "severe", 19: "peak_hour",
    20: "moderate", 21: "moderate", 22: "normal", 23: "normal",
}


@dataclass(frozen=True)
class SimulationResult:
    traffic_record: TrafficRecord
    toll_price: TollPrice
    simulation_time: datetime


def current_simulation_time(settings: TrafficSimulationSettings, now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    if settings.time_mode != "simulated" or settings.simulated_time is None:
        return now.astimezone(MALAYSIA_TIMEZONE)
    anchor = settings.simulated_time_anchor or now
    return (settings.simulated_time + (now - anchor)).astimezone(MALAYSIA_TIMEZONE)


def scenario_for_time(value: datetime) -> str:
    return TIME_PROFILE[value.astimezone(MALAYSIA_TIMEZONE).hour]


def _rules_by_scenario(database: Session) -> dict[str, DynamicPricingRule]:
    return {rule.scenario: rule for rule in database.scalars(select(DynamicPricingRule))}


def run_simulation(
    database: Session,
    settings: TrafficSimulationSettings,
    *,
    source: str,
    scenario: str | None = None,
    now: datetime | None = None,
    seed: int | None = None,
) -> SimulationResult:
    """Persist one simulated traffic record and its price decision atomically."""
    effective_time = current_simulation_time(settings, now)
    selected_scenario = scenario or (
        scenario_for_time(effective_time)
        if settings.simulation_mode == "time_patterned"
        else settings.fixed_scenario
    )
    rules = _rules_by_scenario(database)
    rule = rules.get(selected_scenario)
    if rule is None:
        raise ValueError(f"No dynamic pricing rule exists for {selected_scenario}.")
    generator = random.Random(seed)
    hundredths = generator.randint(
        int(rule.minimum_percentage * 100), int(rule.maximum_percentage * 100)
    )
    percentage = Decimal(hundredths) / Decimal(100)
    capacity = 1000
    vehicle_count = int((percentage * capacity / Decimal(100)).quantize(Decimal(1)))
    traffic = TrafficRecord(
        measured_at=datetime.now(UTC),
        simulation_time=effective_time,
        vehicle_count=vehicle_count,
        road_capacity=capacity,
        congestion_percentage=percentage,
        congestion_category=SCENARIO_CATEGORIES[selected_scenario],
        scenario=selected_scenario,
        source=source,
        simulation_mode=settings.simulation_mode if source == "scheduled" else "manual",
    )
    database.add(traffic)
    database.flush()
    price = TollPrice(
        traffic_record_id=traffic.id,
        effective_at=datetime.now(UTC),
        amount=rule.amount,
        congestion_category=rule.congestion_category,
        rule_version=f"v{settings.pricing_rule_version}",
    )
    database.add(price)
    database.flush()
    return SimulationResult(traffic, price, effective_time)

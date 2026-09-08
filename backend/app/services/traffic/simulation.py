"""Deterministic-friendly traffic simulation and Malaysia-time profile selection."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DynamicPricingRule,
    TollLocation,
    TollPrice,
    TrafficRecord,
    TrafficSimulationSettings,
)
from app.services.locations import default_toll_location_id
from app.services.traffic.pricing import decide_price

MALAYSIA_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")
TIME_PROFILE = {
    0: "normal",
    1: "normal",
    2: "normal",
    3: "normal",
    4: "normal",
    5: "moderate",
    6: "peak_hour",
    7: "severe",
    8: "severe",
    9: "peak_hour",
    10: "moderate",
    11: "moderate",
    12: "moderate",
    13: "moderate",
    14: "moderate",
    15: "moderate",
    16: "peak_hour",
    17: "severe",
    18: "severe",
    19: "peak_hour",
    20: "moderate",
    21: "moderate",
    22: "normal",
    23: "normal",
}

# These are demand multipliers, not congestion categories.  A location's own
# profile turns the shared Malaysia-time pattern into a continuous utilization.
TIME_OF_DAY_MULTIPLIERS = {
    0: Decimal("0.38"),
    1: Decimal("0.36"),
    2: Decimal("0.35"),
    3: Decimal("0.34"),
    4: Decimal("0.38"),
    5: Decimal("0.55"),
    6: Decimal("0.75"),
    7: Decimal("0.95"),
    8: Decimal("1.05"),
    9: Decimal("0.95"),
    10: Decimal("0.78"),
    11: Decimal("0.84"),
    12: Decimal("0.88"),
    13: Decimal("0.86"),
    14: Decimal("0.84"),
    15: Decimal("0.88"),
    16: Decimal("1.00"),
    17: Decimal("1.12"),
    18: Decimal("1.15"),
    19: Decimal("1.00"),
    20: Decimal("0.85"),
    21: Decimal("0.68"),
    22: Decimal("0.50"),
    23: Decimal("0.42"),
}


class TrafficScenarioPredictor(Protocol):
    """Extension point for a future simulated-traffic prediction model."""

    def scenario_for(self, value: datetime) -> str:
        """Return one of the configured traffic scenario keys."""


class TimeProfileScenarioPredictor:
    """Rule-based Malaysia-time profile used until a predictor is introduced."""

    def scenario_for(self, value: datetime) -> str:
        return TIME_PROFILE[value.astimezone(MALAYSIA_TIMEZONE).hour]


DEFAULT_SCENARIO_PREDICTOR = TimeProfileScenarioPredictor()


@dataclass(frozen=True)
class SimulationResult:
    traffic_record: TrafficRecord
    toll_price: TollPrice
    simulation_time: datetime


def current_simulation_time(
    settings: TrafficSimulationSettings, now: datetime | None = None
) -> datetime:
    now = now or datetime.now(UTC)
    if settings.time_mode != "simulated" or settings.simulated_time is None:
        return now.astimezone(MALAYSIA_TIMEZONE)
    anchor = settings.simulated_time_anchor or now
    return (settings.simulated_time + (now - anchor)).astimezone(MALAYSIA_TIMEZONE)


def scenario_for_time(value: datetime) -> str:
    """Resolve the current rule-based scenario; retained as a simple public helper."""
    return DEFAULT_SCENARIO_PREDICTOR.scenario_for(value)


def _rules_by_scenario(database: Session) -> dict[str, DynamicPricingRule]:
    return {rule.scenario: rule for rule in database.scalars(select(DynamicPricingRule))}


def congestion_percentage_for_rule(rule: DynamicPricingRule, *, seed: int | None = None) -> Decimal:
    """Generate a bounded percentage reproducibly when a test seed is supplied."""
    generator = random.Random(seed)
    hundredths = generator.randint(
        int(rule.minimum_percentage * 100), int(rule.maximum_percentage * 100)
    )
    return Decimal(hundredths) / Decimal(100)


def vehicle_count_for_congestion(percentage: Decimal, capacity: int) -> int:
    """Convert a congestion percentage into a whole simulated vehicle count."""
    return int((percentage * capacity / Decimal(100)).quantize(Decimal(1)))


def time_of_day_multiplier(value: datetime) -> Decimal:
    """Return the shared Malaysia-time demand multiplier for one local hour."""
    return TIME_OF_DAY_MULTIPLIERS[value.astimezone(MALAYSIA_TIMEZONE).hour]


def profile_congestion_for_time(
    location: TollLocation, value: datetime, *, seed: int | None = None
) -> Decimal:
    """Calculate one location's bounded, deterministic congestion percentage.

    This is deliberately percentage-first: baseline demand, Malaysia-time demand,
    location peak periods, and a stable per-location time-bucket variation form a
    continuous utilization before any category or pricing rule is selected.
    """
    profile = location.simulation_profile or {}
    baseline = Decimal(str(profile.get("baseline_demand", 0.5)))
    local_bucket = value.astimezone(MALAYSIA_TIMEZONE).replace(second=0, microsecond=0)
    utilization = baseline * time_of_day_multiplier(local_bucket)
    if local_bucket.hour in profile.get("peak_hours", []):
        utilization *= Decimal(str(profile.get("peak_factor", 1)))

    variation = Decimal(str(profile.get("variation", 0.05)))
    bucket_key = local_bucket.strftime("%Y%m%d%H%M")
    generator = random.Random(f"{seed}:{location.code}:{bucket_key}")
    utilization += Decimal(str(generator.uniform(-float(variation), float(variation))))
    return max(Decimal("0"), min(Decimal("100"), utilization * Decimal(100))).quantize(
        Decimal("0.01")
    )


def rule_for_congestion(
    rules: dict[str, DynamicPricingRule], congestion: Decimal
) -> DynamicPricingRule:
    """Select the configured pricing/category band for an already-calculated percentage."""
    return next(
        rule
        for rule in sorted(rules.values(), key=lambda item: item.minimum_percentage)
        if rule.minimum_percentage <= congestion <= rule.maximum_percentage
    )


def profile_congestion_percentage(
    rule: DynamicPricingRule, location: TollLocation, *, seed: int | None = None
) -> Decimal:
    """Return a scenario-bounded percentage for an explicit manual scenario override."""
    profile = location.simulation_profile or {}
    variation = Decimal(str(profile.get("variation", 0.05)))
    low, high = Decimal(rule.minimum_percentage), Decimal(rule.maximum_percentage)
    midpoint = (low + high) / 2
    generator = random.Random(f"{seed}:{location.code}" if seed is not None else None)
    spread = (high - low) * variation
    return max(low, min(high, (midpoint + Decimal(str(generator.uniform(-float(spread), float(spread))))).quantize(Decimal("0.01"))))


def average_speed_for_profile(location: TollLocation, congestion: Decimal) -> Decimal:
    profile = location.simulation_profile or {}
    free_flow = Decimal(str(profile.get("speed_free_flow_kmh", 72)))
    floor = Decimal(str(profile.get("speed_floor_kmh", 20)))
    return max(floor, free_flow - congestion * Decimal("0.55")).quantize(Decimal("0.1"))


def run_simulation(
    database: Session,
    settings: TrafficSimulationSettings,
    *,
    source: str,
    scenario: str | None = None,
    now: datetime | None = None,
    seed: int | None = None,
    scenario_predictor: TrafficScenarioPredictor | None = None,
    location: TollLocation | None = None,
) -> SimulationResult:
    """Persist one simulated traffic record and its price decision atomically."""
    effective_time = current_simulation_time(settings, now)
    predictor = scenario_predictor or DEFAULT_SCENARIO_PREDICTOR
    if location is None:
        location_id = default_toll_location_id(database)
        location = database.get(TollLocation, location_id)
    if location is None:
        raise ValueError("The default Penchala toll location is not initialized. Run migrations.")
    rules = _rules_by_scenario(database)
    if settings.simulation_mode == "time_patterned" and location.simulation_profile and scenario is None:
        percentage = profile_congestion_for_time(location, effective_time, seed=seed)
        rule = rule_for_congestion(rules, percentage)
        selected_scenario = rule.scenario
    else:
        selected_scenario = scenario or (
            predictor.scenario_for(effective_time)
            if settings.simulation_mode == "time_patterned"
            else settings.fixed_scenario
        )
        rule = rules.get(selected_scenario)
        if rule is None:
            raise ValueError(f"No dynamic pricing rule exists for {selected_scenario}.")
        percentage = profile_congestion_percentage(rule, location, seed=seed)
    capacity = location.road_capacity
    vehicle_count = vehicle_count_for_congestion(percentage, capacity)
    traffic = TrafficRecord(
        location_id=location.id,
        measured_at=datetime.now(UTC),
        simulation_time=effective_time,
        vehicle_count=vehicle_count,
        road_capacity=capacity,
        congestion_percentage=percentage,
        congestion_category=rule.congestion_category,
        scenario=selected_scenario,
        source=source,
        simulation_mode=settings.simulation_mode if source == "scheduled" else "manual",
    )
    database.add(traffic)
    database.flush()
    decision = decide_price(database, settings, location, percentage)
    price = TollPrice(
        traffic_record_id=traffic.id,
        location_id=location.id,
        effective_at=datetime.now(UTC),
        amount=decision.amount,
        congestion_category=decision.rule.congestion_category,
        rule_version=f"v{settings.pricing_rule_version}",
    )
    database.add(price)
    database.flush()
    return SimulationResult(traffic, price, effective_time)


def run_network_simulation(
    database: Session, settings: TrafficSimulationSettings, *, source: str, now: datetime | None = None, seed: int | None = None
) -> list[SimulationResult]:
    """Persist independent traffic and pricing records for all generated toll roads."""
    from app.services.traffic.webcam_crossings import is_webcam_toll

    locations = list(database.scalars(select(TollLocation).where(TollLocation.status == "operational").order_by(TollLocation.code)))
    return [
        run_simulation(database, settings, source=source, now=now, seed=seed, location=location)
        for location in locations
        if not is_webcam_toll(location)
    ]

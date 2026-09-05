from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services.traffic.simulation import (
    MALAYSIA_TIMEZONE,
    average_speed_for_profile,
    congestion_percentage_for_rule,
    current_simulation_time,
    location_scenario_for_time,
    profile_congestion_percentage,
    scenario_for_time,
    vehicle_count_for_congestion,
)


def test_time_profile_uses_malaysia_local_hour() -> None:
    # 23:00 UTC is 07:00 in Malaysia, which is the severe morning peak.
    assert scenario_for_time(datetime(2026, 9, 1, 23, tzinfo=UTC)) == "severe"


def test_simulated_clock_advances_from_its_anchor() -> None:
    settings = SimpleNamespace(
        time_mode="simulated",
        simulated_time=datetime(2026, 9, 2, 8, tzinfo=UTC),
        simulated_time_anchor=datetime(2026, 9, 2, 0, tzinfo=UTC),
    )

    actual = current_simulation_time(settings, now=datetime(2026, 9, 2, 2, 30, tzinfo=UTC))

    assert actual == datetime(2026, 9, 2, 18, 30, tzinfo=MALAYSIA_TIMEZONE)


def test_seeded_percentage_and_vehicle_count_are_deterministic() -> None:
    rule = SimpleNamespace(minimum_percentage=30, maximum_percentage=60)

    percentage = congestion_percentage_for_rule(rule, seed=42)

    assert percentage == congestion_percentage_for_rule(rule, seed=42)
    assert 30 <= percentage <= 60
    assert vehicle_count_for_congestion(percentage, 1_000) == int(
        (percentage * 10).quantize(Decimal(1))
    )


def test_location_profiles_can_be_low_and_severe_at_the_same_malaysia_time() -> None:
    at_morning_peak = datetime(2026, 9, 2, 23, tzinfo=UTC)
    quiet = SimpleNamespace(simulation_profile={"baseline_demand": .3, "peak_hours": []})
    busy = SimpleNamespace(simulation_profile={"baseline_demand": .7, "peak_hours": [7], "peak_factor": 1.7})

    assert location_scenario_for_time(quiet, at_morning_peak) == "normal"
    assert location_scenario_for_time(busy, at_morning_peak) == "severe"


def test_profile_variation_and_speed_are_location_specific_and_deterministic() -> None:
    rule = SimpleNamespace(minimum_percentage=0, maximum_percentage=30)
    location = SimpleNamespace(code="NPE", simulation_profile={"variation": .04, "speed_free_flow_kmh": 74, "speed_floor_kmh": 22})
    percentage = profile_congestion_percentage(rule, location, seed=9)

    assert percentage == profile_congestion_percentage(rule, location, seed=9)
    assert average_speed_for_profile(location, Decimal(100)) == Decimal("22.0")

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.api.locations import _profiled_fallback
from app.services.traffic.simulation import (
    MALAYSIA_TIMEZONE,
    average_speed_for_profile,
    congestion_percentage_for_rule,
    current_simulation_time,
    profile_congestion_for_time,
    profile_congestion_percentage,
    rule_for_congestion,
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


def test_profile_congestion_moves_between_bands_over_malaysia_time() -> None:
    location = SimpleNamespace(
        code="TEST",
        simulation_profile={"baseline_demand": .5, "peak_hours": [7, 8, 17, 18], "peak_factor": 1.65, "variation": 0},
    )
    rules = _pricing_rules()

    overnight = profile_congestion_for_time(location, datetime(2026, 9, 2, 18, tzinfo=UTC))  # 02:00 MYT
    midday = profile_congestion_for_time(location, datetime(2026, 9, 2, 2, tzinfo=UTC))  # 10:00 MYT
    morning_peak = profile_congestion_for_time(location, datetime(2026, 9, 1, 23, tzinfo=UTC))  # 07:00 MYT
    severe_peak = profile_congestion_for_time(location, datetime(2026, 9, 2, 0, tzinfo=UTC))  # 08:00 MYT

    assert rule_for_congestion(rules, overnight).scenario == "normal"
    assert rule_for_congestion(rules, midday).scenario == "moderate"
    assert rule_for_congestion(rules, morning_peak).scenario == "peak_hour"
    assert rule_for_congestion(rules, severe_peak).scenario == "severe"


def test_profile_variation_and_speed_are_location_specific_and_deterministic() -> None:
    rule = SimpleNamespace(minimum_percentage=0, maximum_percentage=30)
    location = SimpleNamespace(code="NPE", simulation_profile={"variation": .04, "speed_free_flow_kmh": 74, "speed_floor_kmh": 22})
    percentage = profile_congestion_percentage(rule, location, seed=9)

    assert percentage == profile_congestion_percentage(rule, location, seed=9)
    assert average_speed_for_profile(location, Decimal(100)) == Decimal("22.0")


def _pricing_rules() -> dict[str, SimpleNamespace]:
    return {
        "normal": SimpleNamespace(scenario="normal", minimum_percentage=Decimal("0"), maximum_percentage=Decimal("30"), amount=Decimal(2), congestion_category="low"),
        "moderate": SimpleNamespace(scenario="moderate", minimum_percentage=Decimal("30.01"), maximum_percentage=Decimal("60"), amount=Decimal(3), congestion_category="moderate"),
        "peak_hour": SimpleNamespace(scenario="peak_hour", minimum_percentage=Decimal("60.01"), maximum_percentage=Decimal("80"), amount=Decimal(4), congestion_category="high"),
        "severe": SimpleNamespace(scenario="severe", minimum_percentage=Decimal("80.01"), maximum_percentage=Decimal("100"), amount=Decimal(5), congestion_category="severe"),
    }


def test_profile_congestion_is_deterministic_and_location_independent() -> None:
    at_time = datetime(2026, 9, 2, 9, 20, tzinfo=UTC)
    duke = SimpleNamespace(code="DUKE", simulation_profile={"baseline_demand": .68, "peak_hours": [17], "peak_factor": 1.65, "variation": .08})
    kesas = SimpleNamespace(code="KESAS", simulation_profile={"baseline_demand": .42, "peak_hours": [16, 17], "peak_factor": 1.75, "variation": .05})

    duke_percentage = profile_congestion_for_time(duke, at_time)
    assert duke_percentage == profile_congestion_for_time(duke, at_time.replace(second=55))
    assert duke_percentage != profile_congestion_for_time(kesas, at_time)


def test_rule_for_congestion_uses_configured_threshold_boundaries() -> None:
    rules = _pricing_rules()

    assert rule_for_congestion(rules, Decimal("30")).scenario == "normal"
    assert rule_for_congestion(rules, Decimal("30.01")).scenario == "moderate"
    assert rule_for_congestion(rules, Decimal("60")).scenario == "moderate"
    assert rule_for_congestion(rules, Decimal("60.01")).scenario == "peak_hour"
    assert rule_for_congestion(rules, Decimal("80")).scenario == "peak_hour"
    assert rule_for_congestion(rules, Decimal("80.01")).scenario == "severe"


def test_profiled_fallback_is_independent_and_stable_within_its_minute_bucket() -> None:
    rules = _pricing_rules()
    at_time = datetime(2026, 9, 2, 23, 20, tzinfo=UTC)
    duke = SimpleNamespace(code="DUKE", road_capacity=1200, base_toll=Decimal("2.40"), status="operational", simulation_profile={"baseline_demand": .68, "peak_hours": [7], "peak_factor": 1.65, "variation": .08, "speed_free_flow_kmh": 68, "speed_floor_kmh": 18})
    npe = SimpleNamespace(code="NPE", road_capacity=1300, base_toll=Decimal("2.80"), status="operational", simulation_profile={"baseline_demand": .32, "peak_hours": [8], "peak_factor": 1.25, "variation": .04, "speed_free_flow_kmh": 74, "speed_floor_kmh": 22})

    duke_state = _profiled_fallback(duke, rules, at_time)
    assert duke_state == _profiled_fallback(duke, rules, at_time.replace(second=55))
    assert duke_state["congestion_category"] in {"low", "moderate", "high", "severe"}
    assert duke_state["congestion_percentage"] != _profiled_fallback(npe, rules, at_time)["congestion_percentage"]

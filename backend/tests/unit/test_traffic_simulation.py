from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services.traffic.simulation import (
    MALAYSIA_TIMEZONE,
    congestion_percentage_for_rule,
    current_simulation_time,
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

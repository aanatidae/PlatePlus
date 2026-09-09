from decimal import Decimal

from app.services.demo_feed import crossing_interval_seconds


def test_congestion_controls_demo_crossing_cadence():
    assert crossing_interval_seconds(Decimal("10")) > crossing_interval_seconds(Decimal("35"))
    assert crossing_interval_seconds(Decimal("35")) > crossing_interval_seconds(Decimal("55"))
    assert crossing_interval_seconds(Decimal("55")) > crossing_interval_seconds(Decimal("75"))
    assert crossing_interval_seconds(Decimal("75")) > crossing_interval_seconds(Decimal("95"))


def test_demo_cadence_is_bounded_even_with_jitter():
    assert crossing_interval_seconds(Decimal("100"), jitter=-99) == 0.8
    assert crossing_interval_seconds(Decimal("0"), jitter=0) == 10.0

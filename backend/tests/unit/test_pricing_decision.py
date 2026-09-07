from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from app.services.traffic.pricing import decide_price


class FakeDatabase:
    def __init__(self, rules, previous=None): self.rules, self.previous = rules, previous
    def scalars(self, _statement): return self.rules
    def scalar(self, _statement): return self.previous


def _rule(identifier, low, high, multiplier, category):
    return SimpleNamespace(id=identifier, minimum_percentage=Decimal(str(low)), maximum_percentage=Decimal(str(high)), multiplier=Decimal(str(multiplier)), congestion_category=category)


def test_location_pricing_uses_multiplier_and_clamps_to_policy_limits():
    rules = [_rule("n", 0, 30, 1, "low"), _rule("m", 30.01, 60, 1.5, "moderate"), _rule("p", 60.01, 80, 2, "high"), _rule("s", 80.01, 100, 2.5, "severe")]
    settings = SimpleNamespace(minimum_toll=Decimal("0.50"), maximum_toll_multiplier=Decimal("2.00"), minimum_price_change_minutes=0, pricing_hysteresis_percentage=Decimal("0"))
    location = SimpleNamespace(id="ldp", base_toll=Decimal("2.40"))
    decision = decide_price(FakeDatabase(rules), settings, location, Decimal("90"), datetime.now(UTC))
    assert decision.amount == Decimal("4.80")
    assert decision.rule.congestion_category == "severe"


def test_cooldown_preserves_previous_price_context():
    rules = [_rule("n", 0, 30, 1, "low"), _rule("m", 30.01, 60, 1.5, "moderate"), _rule("p", 60.01, 80, 2, "high"), _rule("s", 80.01, 100, 2.5, "severe")]
    now = datetime.now(UTC); previous = SimpleNamespace(amount=Decimal("3.00"), effective_at=now - timedelta(minutes=2), congestion_category="moderate")
    settings = SimpleNamespace(minimum_toll=Decimal("0.50"), maximum_toll_multiplier=Decimal("3"), minimum_price_change_minutes=5, pricing_hysteresis_percentage=Decimal("2"))
    decision = decide_price(FakeDatabase(rules, previous), settings, SimpleNamespace(id="ldp", base_toll=Decimal("2")), Decimal("75"), now)
    assert decision.amount == Decimal("3.00")
    assert decision.reason == "minimum change interval hold"


def test_pricing_changes_when_a_derived_percentage_crosses_a_band_boundary():
    rules = [_rule("n", 0, 30, 1, "low"), _rule("m", 30.01, 60, 1.5, "moderate"), _rule("p", 60.01, 80, 2, "high"), _rule("s", 80.01, 100, 2.5, "severe")]
    settings = SimpleNamespace(minimum_toll=Decimal("0.50"), maximum_toll_multiplier=Decimal("3"), minimum_price_change_minutes=0, pricing_hysteresis_percentage=Decimal("0"))
    location = SimpleNamespace(id="ldp", base_toll=Decimal("2"))

    normal = decide_price(FakeDatabase(rules), settings, location, Decimal("30"), datetime.now(UTC))
    moderate = decide_price(FakeDatabase(rules), settings, location, Decimal("30.01"), datetime.now(UTC))
    peak = decide_price(FakeDatabase(rules), settings, location, Decimal("60.01"), datetime.now(UTC))
    severe = decide_price(FakeDatabase(rules), settings, location, Decimal("80.01"), datetime.now(UTC))

    assert [decision.amount for decision in (normal, moderate, peak, severe)] == [
        Decimal("2.00"), Decimal("3.00"), Decimal("4.00"), Decimal("5.00")
    ]

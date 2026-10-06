import pytest
from pydantic import ValidationError

from app.schemas.traffic import ManualSimulationRequest, PricingRulesUpdate
from decimal import Decimal


def valid_rules():
    return [
        {"scenario": scenario, "minimum_percentage": low, "maximum_percentage": high, "multiplier": multiplier}
        for scenario, low, high, multiplier in (
            ("normal", "0.00", "30.00", "1.00"),
            ("moderate", "30.01", "60.00", "1.50"),
            ("peak_hour", "60.01", "80.00", "2.50"),
            ("severe", "80.01", "100.00", "3.00"),
        )
    ]


def test_hundredth_ranges_are_exact_and_accepted():
    payload = PricingRulesUpdate(rules=valid_rules())
    assert payload.rules[1].minimum_percentage == Decimal("30.01")
    assert payload.rules[2].multiplier == Decimal("2.50")


@pytest.mark.parametrize("index,field,value", [
    (1, "minimum_percentage", "30"),
    (1, "minimum_percentage", "35"),
    (1, "minimum_percentage", "31"),
    (3, "maximum_percentage", "105"),
    (0, "minimum_percentage", "-0.01"),
    (2, "multiplier", "-1"),
    (2, "multiplier", "0"),
    (2, "multiplier", "10.01"),
    (1, "minimum_percentage", "30.001"),
    (2, "multiplier", "2.501"),
    (0, "minimum_percentage", "0.01"),
    (3, "maximum_percentage", "99.99"),
    (1, "maximum_percentage", "29.00"),
])
def test_invalid_pricing_rules_are_rejected(index, field, value):
    rules = valid_rules()
    rules[index][field] = value
    with pytest.raises(ValidationError):
        PricingRulesUpdate(rules=rules)


def test_pricing_rules_require_contiguous_complete_ranges() -> None:
    with pytest.raises(ValidationError, match="contiguous"):
        PricingRulesUpdate(
            rules=[
                {"scenario": "normal", "minimum_percentage": "0", "maximum_percentage": "30", "multiplier": "1"},
                {"scenario": "moderate", "minimum_percentage": "30.02", "maximum_percentage": "60", "multiplier": "1.5"},
                {"scenario": "peak_hour", "minimum_percentage": "60.01", "maximum_percentage": "80", "multiplier": "2"},
                {"scenario": "severe", "minimum_percentage": "80.01", "maximum_percentage": "100", "multiplier": "2.5"},
            ]
        )


def test_manual_simulation_uses_saved_settings_when_no_scenario_is_supplied() -> None:
    assert ManualSimulationRequest().scenario is None

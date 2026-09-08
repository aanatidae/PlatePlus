import pytest
from pydantic import ValidationError

from app.schemas.traffic import ManualSimulationRequest, PricingRulesUpdate


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

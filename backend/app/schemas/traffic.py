"""Schemas for simulated traffic, pricing, and scheduler administration."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from itertools import pairwise
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Scenario = Literal["normal", "moderate", "peak_hour", "severe"]
SimulationMode = Literal["time_patterned", "fixed_scenario"]
TimeMode = Literal["real", "simulated"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SimulationSettingsUpdate(BaseModel):
    is_enabled: bool
    interval_minutes: Literal[1, 5, 15]
    simulation_mode: SimulationMode
    fixed_scenario: Scenario
    time_mode: TimeMode
    simulated_time: datetime | None = None

    @model_validator(mode="after")
    def require_simulated_time(self) -> SimulationSettingsUpdate:
        if self.time_mode == "simulated" and self.simulated_time is None:
            raise ValueError("simulated_time is required when time_mode is simulated")
        return self


class SimulationSettingsRead(ORMModel):
    id: UUID
    is_enabled: bool
    interval_minutes: int
    simulation_mode: str
    fixed_scenario: str
    time_mode: str
    simulated_time: datetime | None
    simulated_time_anchor: datetime | None
    pricing_rule_version: int
    created_at: datetime
    updated_at: datetime
    current_simulation_time: datetime


class PricingRuleUpdate(BaseModel):
    scenario: Scenario
    minimum_percentage: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    maximum_percentage: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    amount: Decimal = Field(ge=0, max_digits=8, decimal_places=2)

    @model_validator(mode="after")
    def valid_range(self) -> PricingRuleUpdate:
        if self.minimum_percentage > self.maximum_percentage:
            raise ValueError("minimum_percentage cannot exceed maximum_percentage")
        return self


class PricingRulesUpdate(BaseModel):
    rules: list[PricingRuleUpdate] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def require_all_scenarios_and_contiguous_ranges(self) -> PricingRulesUpdate:
        expected = {"normal", "moderate", "peak_hour", "severe"}
        scenarios = {rule.scenario for rule in self.rules}
        if scenarios != expected or len(scenarios) != len(self.rules):
            raise ValueError("exactly one rule for each fixed scenario is required")
        ordered = sorted(self.rules, key=lambda rule: rule.minimum_percentage)
        if ordered[0].minimum_percentage != 0 or ordered[-1].maximum_percentage != 100:
            raise ValueError("pricing ranges must cover 0 through 100 percent")
        for previous, current in pairwise(ordered):
            if current.minimum_percentage != previous.maximum_percentage + Decimal("0.01"):
                raise ValueError("pricing ranges must be contiguous without overlaps or gaps")
        return self


class PricingRuleRead(ORMModel):
    id: UUID
    scenario: str
    congestion_category: str
    minimum_percentage: Decimal
    maximum_percentage: Decimal
    amount: Decimal
    created_at: datetime
    updated_at: datetime


class ManualSimulationRequest(BaseModel):
    scenario: Scenario | None = None


class SimulationRunRead(BaseModel):
    traffic_record_id: UUID
    toll_price_id: UUID
    scenario: str
    congestion_percentage: Decimal
    congestion_category: str
    amount: Decimal
    simulation_time: datetime
    source: str


class AuditLogRead(ORMModel):
    id: UUID
    admin_id: UUID | None
    action: str
    entity_type: str
    details_json: str
    created_at: datetime

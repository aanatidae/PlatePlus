"""Location-aware, explainable rule pricing for simulated traffic."""
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DynamicPricingRule, TollLocation, TollPrice, TrafficSimulationSettings

@dataclass(frozen=True)
class PricingDecision:
    rule: DynamicPricingRule
    previous_amount: Decimal | None
    amount: Decimal
    reason: str

def decide_price(database: Session, settings: TrafficSimulationSettings, location: TollLocation, congestion: Decimal, now: datetime | None = None) -> PricingDecision:
    now = now or datetime.now(UTC)
    rules = list(database.scalars(select(DynamicPricingRule).order_by(DynamicPricingRule.minimum_percentage)))
    candidate = next(rule for rule in rules if rule.minimum_percentage <= congestion <= rule.maximum_percentage)
    previous = database.scalar(select(TollPrice).where(TollPrice.location_id == location.id).order_by(TollPrice.effective_at.desc()))
    selected = candidate; reason = "current congestion band"
    if previous is not None:
        previous_rule = next((rule for rule in rules if rule.congestion_category == previous.congestion_category), candidate)
        elapsed = (now - previous.effective_at).total_seconds() / 60
        if elapsed < settings.minimum_price_change_minutes:
            selected, reason = previous_rule, "minimum change interval hold"
        elif selected.id != previous_rule.id:
            boundary = selected.minimum_percentage if selected.minimum_percentage > previous_rule.minimum_percentage else previous_rule.minimum_percentage
            if abs(congestion - boundary) < settings.pricing_hysteresis_percentage:
                selected, reason = previous_rule, "hysteresis hold near band boundary"
    raw = location.base_toll * selected.multiplier
    ceiling = location.base_toll * settings.maximum_toll_multiplier
    amount = max(settings.minimum_toll, min(raw, ceiling)).quantize(Decimal("0.01"))
    return PricingDecision(selected, previous.amount if previous else None, amount, reason)

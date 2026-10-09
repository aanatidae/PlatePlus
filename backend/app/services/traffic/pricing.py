"""Location-aware, explainable rule pricing for simulated traffic."""
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DynamicPricingRule,
    TollLocation,
    TollPrice,
    TrafficRecord,
    TrafficSimulationSettings,
)


@dataclass(frozen=True)
class PricingDecision:
    rule: DynamicPricingRule
    previous_amount: Decimal | None
    amount: Decimal
    reason: str

def decide_price(database: Session, settings: TrafficSimulationSettings, location: TollLocation, congestion: Decimal, now: datetime | None = None, *, context: Literal["traffic", "policy_update", "webcam_crossing", "webcam_crossing_expiry"] = "traffic") -> PricingDecision:
    now = now or datetime.now(UTC)
    rules = list(database.scalars(select(DynamicPricingRule).order_by(DynamicPricingRule.minimum_percentage)))
    candidate = next(rule for rule in rules if rule.minimum_percentage <= congestion <= rule.maximum_percentage)
    previous = database.scalar(select(TollPrice).where(TollPrice.location_id == location.id, TollPrice.effective_at <= now).order_by(TollPrice.effective_at.desc(), TollPrice.created_at.desc(), TollPrice.id.desc()).limit(1))
    selected = candidate; reason = "pricing policy updated" if context == "policy_update" else "current congestion band"
    if context in {"webcam_crossing", "webcam_crossing_expiry"}:
        if location.code != "SIMULATOR":
            raise ValueError("Crossing pricing context is restricted to Simulator Toll Plaza.")
        reason = "accepted crossing band" if context == "webcam_crossing" else "active crossing window band"
    if previous is not None and context == "traffic":
        previous_rule = next((rule for rule in rules if rule.congestion_category == previous.congestion_category), candidate)
        elapsed = (now - previous.effective_at).total_seconds() / 60
        if elapsed < settings.minimum_price_change_minutes:
            selected, reason = previous_rule, "minimum change interval hold"
        elif selected.id != previous_rule.id:
            boundary = max(previous_rule.minimum_percentage, selected.minimum_percentage)
            if abs(congestion - boundary) < settings.pricing_hysteresis_percentage:
                selected, reason = previous_rule, "hysteresis hold near band boundary"
    raw = location.base_toll * selected.multiplier
    ceiling = location.base_toll * settings.maximum_toll_multiplier
    amount = max(settings.minimum_toll, min(raw, ceiling)).quantize(Decimal("0.01"))
    if raw < settings.minimum_toll:
        reason += "; minimum toll floor applied"
    elif raw > ceiling:
        reason += "; maximum multiplier cap applied"
    return PricingDecision(selected, previous.amount if previous else None, amount, reason)


def reprice_current_locations(database: Session, settings: TrafficSimulationSettings, now: datetime | None = None) -> None:
    """Append authoritative prices using existing congestion, atomically with the policy edit.

    This creates no traffic, crossings or payments and never changes historical records.
    """
    from app.services.operations import record_event
    from app.services.traffic.simulation import profile_congestion_for_time
    from app.services.traffic.webcam_crossings import active_crossing_congestion, is_webcam_toll

    now = now or datetime.now(UTC)
    database.flush()  # Decisions must see all four newly configured rules.
    locations = database.scalars(select(TollLocation).where(
        TollLocation.status == "operational"
    ).order_by(TollLocation.id).with_for_update())
    for location in locations:
        traffic = database.scalar(select(TrafficRecord).where(
            TrafficRecord.location_id == location.id
        ).order_by(TrafficRecord.measured_at.desc()).limit(1))
        if is_webcam_toll(location):
            _, congestion = active_crossing_congestion(database, location, now)
        elif traffic is not None:
            congestion = traffic.congestion_percentage
        else:
            # Same minute-bucketed canonical fallback used by location telemetry.
            congestion = profile_congestion_for_time(location, now.replace(second=0, microsecond=0))
        previous = database.scalar(select(TollPrice).where(
            TollPrice.location_id == location.id
        ).order_by(TollPrice.effective_at.desc()).limit(1))
        decision = decide_price(database, settings, location, congestion, now, context="policy_update")
        database.add(TollPrice(
            location_id=location.id, traffic_record_id=traffic.id if traffic and not is_webcam_toll(location) else None,
            effective_at=now, amount=decision.amount,
            congestion_category=decision.rule.congestion_category,
            rule_version=f"v{settings.pricing_rule_version}",
        ))
        if previous is None or previous.amount != decision.amount or previous.congestion_category != decision.rule.congestion_category:
            record_event(database, event_type="pricing_change", severity="information", source="admin",
                location_id=location.id, message="Dynamic simulated toll repriced after a pricing policy update.",
                details={"previous": previous.amount if previous else None, "new": decision.amount,
                         "previous_category": previous.congestion_category if previous else None,
                         "category": decision.rule.congestion_category, "congestion": congestion,
                         "rule_version": settings.pricing_rule_version, "reason": decision.reason})

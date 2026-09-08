"""Administrator endpoints for traffic simulation and dynamic pricing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.db.session import get_db
from app.models import (
    Admin,
    AdminAuditLog,
    DynamicPricingRule,
    TollPrice,
    TrafficRecord,
    TrafficSimulationSettings,
    TollLocation,
)
from app.schemas.traffic import (
    AuditLogRead,
    ManualSimulationRequest,
    PricingRuleRead,
    PricingRulesUpdate,
    SimulationRunRead,
    SimulationSettingsRead,
    SimulationSettingsUpdate,
)
from app.services.traffic.simulation import current_simulation_time, run_simulation
from app.services.traffic.pricing import decide_price
from app.services.operations import record_event

router = APIRouter(prefix="/api/traffic", tags=["traffic"], dependencies=[Depends(require_admin)])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[Admin, Depends(require_admin)]


def _settings(database: Session) -> TrafficSimulationSettings:
    settings = database.scalar(
        select(TrafficSimulationSettings).where(
            TrafficSimulationSettings.singleton_key == "default"
        )
    )
    if settings is None:
        raise HTTPException(
            status_code=503, detail="Traffic simulation is not initialized. Run migrations."
        )
    return settings


def _read_settings(settings: TrafficSimulationSettings) -> SimulationSettingsRead:
    return SimulationSettingsRead(
        **{
            field: getattr(settings, field)
            for field in SimulationSettingsRead.model_fields
            if field != "current_simulation_time"
        },
        current_simulation_time=current_simulation_time(settings),
    )


def _audit(database: Session, admin: Admin, action: str, entity_type: str, details: dict) -> None:
    database.add(
        AdminAuditLog(
            admin_id=admin.id,
            action=action,
            entity_type=entity_type,
            details_json=json.dumps(details, default=str),
        )
    )


@router.get("/settings", response_model=SimulationSettingsRead)
def get_settings(database: DatabaseSession):
    return _read_settings(_settings(database))


@router.put("/settings", response_model=SimulationSettingsRead)
def update_settings(
    payload: SimulationSettingsUpdate, database: DatabaseSession, admin: CurrentAdmin
):
    settings = _settings(database)
    was_enabled = settings.is_enabled
    settings.is_enabled = payload.is_enabled
    settings.interval_minutes = payload.interval_minutes
    settings.simulation_mode = payload.simulation_mode
    settings.fixed_scenario = payload.fixed_scenario
    settings.time_mode = payload.time_mode
    settings.simulated_time = payload.simulated_time if payload.time_mode == "simulated" else None
    settings.simulated_time_anchor = datetime.now(UTC) if payload.time_mode == "simulated" else None
    settings.minimum_toll = payload.minimum_toll
    settings.maximum_toll_multiplier = payload.maximum_toll_multiplier
    settings.minimum_price_change_minutes = payload.minimum_price_change_minutes
    settings.pricing_hysteresis_percentage = payload.pricing_hysteresis_percentage
    _audit(
        database,
        admin,
        "traffic_settings_updated",
        "traffic_simulation_settings",
        payload.model_dump(mode="json"),
    )
    if payload.is_enabled and not was_enabled:
        result = run_simulation(database, settings, source="scheduled")
        _audit(
            database,
            admin,
            "traffic_simulation_run",
            "traffic_record",
            {"source": "scheduled", "traffic_record_id": result.traffic_record.id},
        )
        record_event(database, event_type="simulation_run", severity="information", source="simulated", location_id=result.traffic_record.location_id, message="Scheduled simulated traffic run completed.", details={"scenario": result.traffic_record.scenario, "congestion": result.traffic_record.congestion_percentage, "toll": result.toll_price.amount, "admin_id": admin.id})
    database.commit()
    database.refresh(settings)
    return _read_settings(settings)


@router.get("/pricing-rules", response_model=list[PricingRuleRead])
def list_pricing_rules(database: DatabaseSession):
    return list(
        database.scalars(select(DynamicPricingRule).order_by(DynamicPricingRule.minimum_percentage))
    )


@router.get("/pricing-preview")
def pricing_preview(
    location_id: UUID, database: DatabaseSession, congestion_percentage: Decimal = Query(ge=0, le=100)
):
    location = database.get(TollLocation, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Toll location was not found.")
    decision = decide_price(database, _settings(database), location, congestion_percentage)
    return {"location_id": location_id, "congestion_percentage": congestion_percentage,
            "congestion_category": decision.rule.congestion_category, "base_toll": location.base_toll,
            "multiplier": decision.rule.multiplier, "previous_toll": decision.previous_amount,
            "new_toll": decision.amount, "reason": decision.reason}


@router.put("/pricing-rules", response_model=list[PricingRuleRead])
def update_pricing_rules(
    payload: PricingRulesUpdate, database: DatabaseSession, admin: CurrentAdmin
):
    rules = {rule.scenario: rule for rule in database.scalars(select(DynamicPricingRule))}
    if set(rules) != {item.scenario for item in payload.rules}:
        raise HTTPException(
            status_code=503, detail="Dynamic pricing rules are not initialized. Run migrations."
        )
    for item in payload.rules:
        rule = rules[item.scenario]
        rule.minimum_percentage = item.minimum_percentage
        rule.maximum_percentage = item.maximum_percentage
        rule.multiplier = item.multiplier
    settings = _settings(database)
    settings.pricing_rule_version += 1
    latest_traffic = database.scalar(
        select(TrafficRecord).order_by(TrafficRecord.measured_at.desc())
    )
    if latest_traffic is not None:
        location = latest_traffic.location
        decision = decide_price(database, settings, location, latest_traffic.congestion_percentage)
        if decision.previous_amount != decision.amount:
            record_event(database, event_type="pricing_change", severity="information", source="simulated", location_id=latest_traffic.location_id, message="Dynamic simulated toll price changed.", details={"previous": decision.previous_amount, "new": decision.amount, "congestion": latest_traffic.congestion_percentage, "category": decision.rule.congestion_category, "rule_version": settings.pricing_rule_version, "admin_id": admin.id})
        database.add(
            TollPrice(
                traffic_record_id=latest_traffic.id,
                location_id=latest_traffic.location_id,
                effective_at=datetime.now(UTC),
                amount=decision.amount,
                congestion_category=decision.rule.congestion_category,
                rule_version=f"v{settings.pricing_rule_version}",
            )
        )
    _audit(
        database,
        admin,
        "pricing_rules_updated",
        "dynamic_pricing_rules",
        payload.model_dump(mode="json"),
    )
    record_event(database, event_type="administrator_action", source="admin", message="Administrator updated pricing rules.", details={"action": "pricing_rules_updated", "admin_id": admin.id})
    database.commit()
    return list(
        database.scalars(select(DynamicPricingRule).order_by(DynamicPricingRule.minimum_percentage))
    )


@router.post("/simulate", response_model=SimulationRunRead, status_code=status.HTTP_201_CREATED)
def manual_simulation(
    payload: ManualSimulationRequest, database: DatabaseSession, admin: CurrentAdmin
):
    result = run_simulation(
        database, _settings(database), source="manual", scenario=payload.scenario
    )
    _audit(
        database,
        admin,
        "traffic_simulation_run",
        "traffic_record",
        {
            "source": "manual",
            "scenario": result.traffic_record.scenario,
            "traffic_record_id": result.traffic_record.id,
        },
    )
    record_event(database, event_type="simulation_run", severity="information", source="simulated", location_id=result.traffic_record.location_id, message="Manual simulated traffic run completed.", details={"scenario": result.traffic_record.scenario, "congestion": result.traffic_record.congestion_percentage, "toll": result.toll_price.amount, "admin_id": admin.id})
    database.commit()
    return SimulationRunRead(
        traffic_record_id=result.traffic_record.id,
        toll_price_id=result.toll_price.id,
        scenario=result.traffic_record.scenario,
        congestion_percentage=result.traffic_record.congestion_percentage,
        congestion_category=result.traffic_record.congestion_category,
        amount=result.toll_price.amount,
        simulation_time=result.simulation_time,
        source="manual",
    )


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(database: DatabaseSession):
    return list(
        database.scalars(select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(100))
    )

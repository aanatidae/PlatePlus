"""Administrator endpoints for traffic simulation and dynamic pricing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
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
    database.commit()
    database.refresh(settings)
    return _read_settings(settings)


@router.get("/pricing-rules", response_model=list[PricingRuleRead])
def list_pricing_rules(database: DatabaseSession):
    return list(
        database.scalars(select(DynamicPricingRule).order_by(DynamicPricingRule.minimum_percentage))
    )


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
        rule.amount = item.amount
    settings = _settings(database)
    settings.pricing_rule_version += 1
    latest_traffic = database.scalar(
        select(TrafficRecord).order_by(TrafficRecord.measured_at.desc())
    )
    if latest_traffic is not None:
        matching = next(
            item
            for item in payload.rules
            if item.minimum_percentage
            <= latest_traffic.congestion_percentage
            <= item.maximum_percentage
        )
        database.add(
            TollPrice(
                traffic_record_id=latest_traffic.id,
                location_id=latest_traffic.location_id,
                effective_at=datetime.now(UTC),
                amount=matching.amount,
                congestion_category=rules[matching.scenario].congestion_category,
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

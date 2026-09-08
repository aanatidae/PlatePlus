"""Protected operational-alert monitoring and demo controls."""
from datetime import UTC, datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.api.auth import require_admin
from app.db.session import get_db
from app.models import Admin, OperationalAlert, OperationalEvent, TollLocation
from app.services.operations import emit, evaluate, record_event

router = APIRouter(prefix="/api/operations", tags=["operations"], dependencies=[Depends(require_admin)])
DatabaseSession = Annotated[Session, Depends(get_db)]

def serialize(alert): return {"id": str(alert.id), "location_id": str(alert.location_id) if alert.location_id else None, "alert_type": alert.alert_type, "severity": alert.severity, "status": alert.status, "title": alert.title, "message": alert.message, "source": alert.source, "started_at": alert.started_at, "last_seen_at": alert.last_seen_at, "acknowledged_at": alert.acknowledged_at}

@router.post("/monitor")
def monitor(database: DatabaseSession):
    evaluate(database); return {"status": "evaluated"}

@router.get("/alerts")
def alerts(database: DatabaseSession, location_id: str | None = None, severity: str | None = None, alert_type: str | None = None, acknowledged: bool | None = None, status: str | None = None, source: str | None = None, start_at: datetime | None = None, end_at: datetime | None = None):
    statement = select(OperationalAlert).order_by(OperationalAlert.last_seen_at.desc())
    if location_id: statement = statement.where(OperationalAlert.location_id == location_id)
    if severity: statement = statement.where(OperationalAlert.severity == severity)
    if alert_type: statement = statement.where(OperationalAlert.alert_type == alert_type)
    if acknowledged is not None: statement = statement.where(OperationalAlert.acknowledged_at.is_not(None) if acknowledged else OperationalAlert.acknowledged_at.is_(None))
    if status: statement = statement.where(OperationalAlert.status == status)
    if source: statement = statement.where(OperationalAlert.source == source)
    if start_at: statement = statement.where(OperationalAlert.started_at >= start_at)
    if end_at: statement = statement.where(OperationalAlert.started_at <= end_at)
    return [serialize(item) for item in database.scalars(statement.limit(200))]

@router.get("/events")
def events(database: DatabaseSession, location_id: str | None = None, event_type: str | None = None, severity: str | None = None, source: str | None = None, start_at: datetime | None = None, end_at: datetime | None = None):
    statement = select(OperationalEvent).order_by(OperationalEvent.occurred_at.desc())
    if location_id: statement = statement.where(OperationalEvent.location_id == location_id)
    if event_type: statement = statement.where(OperationalEvent.event_type == event_type)
    if severity: statement = statement.where(OperationalEvent.severity == severity)
    if source: statement = statement.where(OperationalEvent.source == source)
    if start_at: statement = statement.where(OperationalEvent.occurred_at >= start_at)
    if end_at: statement = statement.where(OperationalEvent.occurred_at <= end_at)
    return [{"id": str(item.id), "location_id": str(item.location_id) if item.location_id else None, "event_type": item.event_type, "severity": item.severity, "source": item.source, "message": item.message, "occurred_at": item.occurred_at} for item in database.scalars(statement.limit(200))]

@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: str, database: DatabaseSession, admin: Admin = Depends(require_admin)):
    alert = database.get(OperationalAlert, alert_id)
    if not alert: raise HTTPException(status_code=404, detail="Operational alert was not found.")
    alert.status = "acknowledged"; alert.acknowledged_at = datetime.now(UTC); alert.acknowledged_by_admin_id = admin.id
    record_event(database, event_type="administrator_action", source="admin", message="Administrator acknowledged an operational alert.", location_id=alert.location_id, alert_id=alert.id, details={"action": "alert_acknowledged", "admin_id": admin.id})
    database.commit(); return serialize(alert)

@router.post("/alerts/seed-demo")
def seed_demo(database: DatabaseSession):
    locations = list(database.scalars(select(TollLocation).order_by(TollLocation.display_name)))
    if not locations: raise HTTPException(status_code=409, detail="Toll locations must be seeded first.")
    samples = (("severe_congestion", "critical", "Severe congestion", "Demo: simulated severe congestion.", locations[0]), ("camera_outage", "critical", "Camera unavailable", "Demo: simulated camera outage.", locations[min(1, len(locations)-1)]), ("repeated_low_confidence", "warning", "Repeated low-confidence ALPR", "Demo: 3 low-confidence reads in 15 minutes.", locations[0]), ("repeated_failed_payment", "warning", "Repeated failed simulated payments", "Demo: 3 failed payments in 15 minutes.", locations[min(1, len(locations)-1)]), ("backend_api_error", "warning", "Backend/API warning", "Demo: simulated recoverable API issue.", None))
    for kind, severity, title, message, location in samples: emit(database, alert_type=kind, severity=severity, title=title, message=message, location_id=location.id if location else None, source="demo", incident_key=f"demo:{kind}:{location.id if location else 'network'}")
    record_event(database, event_type="administrator_action", source="admin", message="Demo alerts seeded.", details={"action": "seed_demo_alerts"})
    database.commit(); return {"status": "seeded"}

@router.post("/alerts/reset-demo")
def reset_demo(database: DatabaseSession):
    ids = list(database.scalars(select(OperationalAlert.id).where(OperationalAlert.source == "demo")))
    if ids: database.execute(delete(OperationalEvent).where(OperationalEvent.alert_id.in_(ids), OperationalEvent.source == "demo")); database.execute(delete(OperationalAlert).where(OperationalAlert.id.in_(ids)))
    record_event(database, event_type="administrator_action", source="admin", message="Demo alerts reset.", details={"action": "reset_demo_alerts"})
    database.commit()
    return {"status": "reset"}

"""Condition-based alert evaluation for the simulated PlatePlus operations screen."""
from datetime import UTC, datetime, timedelta
import json
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import DetectionRecord, OperationalAlert, OperationalEvent, TollLocation, TollTransaction

WINDOW = timedelta(minutes=15)
RUNTIME_HEALTH: dict[str, dict] = {}

def record_event(database: Session, *, event_type: str, message: str, severity="information", location_id=None, source="detected", details: dict | None = None, alert_id=None) -> OperationalEvent:
    event = OperationalEvent(location_id=location_id, alert_id=alert_id, event_type=event_type, severity=severity, source=source, message=message, details_json=json.dumps(details or {}, default=str), occurred_at=datetime.now(UTC))
    database.add(event); return event

def emit(database: Session, *, alert_type: str, severity: str, title: str, message: str, location_id=None, source="detected", incident_key: str | None = None) -> OperationalAlert:
    now = datetime.now(UTC); key = incident_key or f"{source}:{alert_type}:{location_id or 'network'}:{severity}"
    alert = database.scalar(select(OperationalAlert).where(OperationalAlert.incident_key == key))
    if alert is None:
        alert = OperationalAlert(location_id=location_id, alert_type=alert_type, severity=severity, title=title, message=message, source=source, incident_key=key, started_at=now, last_seen_at=now)
        database.add(alert); database.flush()
        record_event(database, location_id=location_id, alert_id=alert.id, event_type=alert_type, severity=severity, source=source, message=message)
    else:
        alert.last_seen_at = now; alert.message = message
    return alert

def evaluate(database: Session) -> list[OperationalAlert]:
    from app.api.locations import _state
    now = datetime.now(UTC); alerts: list[OperationalAlert] = []
    for location in database.scalars(select(TollLocation)):
        state = _state(database, location); telemetry = state["telemetry"]
        if telemetry and float(telemetry["congestion_percentage"]) > 80:
            alerts.append(emit(database, alert_type="severe_congestion", severity="critical", title="Severe congestion", message=f"{location.display_name} is at {telemetry['congestion_percentage']}% simulated congestion.", location_id=location.id))
        elif telemetry:
            alert = database.scalar(select(OperationalAlert).where(OperationalAlert.location_id == location.id, OperationalAlert.alert_type == "severe_congestion", OperationalAlert.status != "resolved"))
            if alert:
                alert.status = "resolved"; record_event(database, event_type="congestion_recovered", location_id=location.id, alert_id=alert.id, message=f"Severe congestion cleared at {location.display_name}.")
        if telemetry and telemetry.get("camera_status") == "offline" and location.status == "operational":
            alerts.append(emit(database, alert_type="camera_outage", severity="critical", title="Camera unavailable", message=f"Camera telemetry is unavailable at {location.display_name}.", location_id=location.id))
        elif telemetry and telemetry.get("camera_status") == "online":
            alert = database.scalar(select(OperationalAlert).where(OperationalAlert.location_id == location.id, OperationalAlert.alert_type == "camera_outage", OperationalAlert.status != "resolved"))
            if alert:
                alert.status = "resolved"; record_event(database, event_type="camera_restored", location_id=location.id, alert_id=alert.id, message=f"Camera restored at {location.display_name}.")
        low = database.scalars(select(DetectionRecord).where(DetectionRecord.location_id == location.id, DetectionRecord.detected_at >= now - WINDOW, DetectionRecord.status == "low_confidence")).all()
        failed = database.scalars(select(TollTransaction).where(TollTransaction.location_id == location.id, TollTransaction.processed_at >= now - WINDOW, TollTransaction.status.in_(("failed", "insufficient_balance")))).all()
        for kind, rows, title in (("repeated_low_confidence", low, "Repeated low-confidence ALPR"), ("repeated_failed_payment", failed, "Repeated failed simulated payments")):
            if len(rows) >= 3:
                severity = "critical" if len(rows) >= 5 else "warning"
                alerts.append(emit(database, alert_type=kind, severity=severity, title=title, message=f"{len(rows)} events occurred at {location.display_name} in the last 15 minutes.", location_id=location.id))
    database.commit(); return alerts

def record_failure(component: str, operation: str, error: Exception | str, *, database: Session | None = None, location_id=None) -> None:
    """Coalesce safe failure details; retain runtime health if PostgreSQL cannot persist."""
    message = str(error).split("\n", 1)[0][:180]
    message = re.sub(r"(?i)(token|authorization|password|secret|postgresql\+\w+://)[^\s,;]*", r"\1=[redacted]", message)
    message = message or "Operational component unavailable."
    key = f"failure:{component}:{operation}:{location_id or 'network'}"; now = datetime.now(UTC)
    state = RUNTIME_HEALTH.setdefault(key, {"count": 0, "last_seen": now})
    state["count"] += 1; state["last_seen"] = now
    severity = "critical" if component == "database" or state["count"] >= 3 else "warning"
    if database is None: return
    try:
        emit(database, alert_type=f"{component}_error", severity=severity, title=f"{component.title()} unavailable", message=f"{operation}: {message}", location_id=location_id, incident_key=key)
        if state["count"] == 3:
            record_event(database, event_type=f"{component}_error", severity=severity, message=f"{operation}: {message}", location_id=location_id, details={"component": component, "operation": operation, "count": state["count"]})
        database.commit()
    except Exception:
        database.rollback()

def record_recovery(database: Session, component: str, operation: str, *, location_id=None) -> None:
    key = f"failure:{component}:{operation}:{location_id or 'network'}"
    if key not in RUNTIME_HEALTH: return
    RUNTIME_HEALTH.pop(key, None)
    alert = database.scalar(select(OperationalAlert).where(OperationalAlert.incident_key == key))
    if alert:
        alert.status = "resolved"; alert.last_seen_at = datetime.now(UTC)
        record_event(database, event_type=f"{component}_recovered", severity="information", message=f"{component.title()} recovered for {operation}.", location_id=location_id, alert_id=alert.id)

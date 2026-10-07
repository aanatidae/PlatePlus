"""Condition-based alert evaluation for the simulated PlatePlus operations screen."""
import json
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DetectionRecord,
    OperationalAlert,
    OperationalEvent,
    TollLocation,
    TollTransaction,
)

WINDOW = timedelta(minutes=15)
RUNTIME_HEALTH: dict[str, dict] = {}
ORIGIN_REJECTION_REASONS = {"ambiguous_supported_patterns", "unsupported_plate_pattern"}


def _repeated_failure_rollup(database, location, kind, rows, now):
    """One incident per location/type; origin failures do not create extra alerts."""
    key = f"detected:{kind}:{location.id}:aggregate"
    previous = database.scalar(select(OperationalAlert).where(OperationalAlert.incident_key == key))
    if previous is None:
        # Reuse an existing pre-V3 severity-keyed incident instead of duplicating it.
        legacy = list(database.scalars(select(OperationalAlert).where(
            OperationalAlert.location_id == location.id, OperationalAlert.alert_type == kind,
            OperationalAlert.source == "detected", OperationalAlert.status != "resolved",
        ).order_by(OperationalAlert.started_at)))
        if legacy:
            previous = legacy[0]
            previous.incident_key = key
            for duplicate in legacy[1:]:
                duplicate.status = "resolved"
                duplicate.last_seen_at = now
                record_event(database, event_type=f"{kind}_coalesced", location_id=location.id,
                             alert_id=duplicate.id, message="Legacy repeated-failure incidents combined into one location rollup.")
            database.flush()
    if len(rows) < 3:
        if previous and previous.status != "resolved":
            previous.status = "resolved"
            previous.last_seen_at = now
            record_event(database, event_type=f"{kind}_recovered", location_id=location.id,
                         alert_id=previous.id, message=f"Repeated recognition/payment condition cleared at {location.display_name}.")
        return None
    origin_rejections = sum(
        getattr(row, "plate_origin", None) == "unknown"
        and getattr(row, "origin_reason", None) in ORIGIN_REJECTION_REASONS
        for row in rows
    ) if kind == "repeated_low_confidence" else 0
    severity = "critical" if len(rows) - origin_rejections >= 5 else "warning"
    title = "Repeated low-confidence ALPR" if kind == "repeated_low_confidence" else "Repeated failed simulated payments"
    if origin_rejections:
        title = "Repeated plate-origin rejections" if origin_rejections == len(rows) else "Repeated ALPR rejections"
    message = f"{len(rows)} events occurred at {location.display_name} in the last 15 minutes."
    if origin_rejections:
        message += f" {origin_rejections} were ambiguous or unsupported plate-origin patterns; they were safely rejected without a deduction."
    old_status = previous.status if previous else None
    old_severity = previous.severity if previous else None
    alert = emit(database, alert_type=kind, severity=severity, title=title, message=message,
                 location_id=location.id, incident_key=key)
    alert.severity = severity
    alert.title = title
    if old_status == "resolved":
        alert.status = "active"
        alert.started_at = now
        alert.acknowledged_at = None
        alert.acknowledged_by_admin_id = None
        record_event(database, event_type=f"{kind}_recurred", severity=severity,
                     location_id=location.id, alert_id=alert.id, message=message)
    elif previous and old_severity != severity:
        record_event(database, event_type=f"{kind}_severity_changed", severity=severity,
                     location_id=location.id, alert_id=alert.id, message=message)
    return alert

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
    for location in database.scalars(select(TollLocation).where(TollLocation.status != "retired")):
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
        low = database.scalars(select(DetectionRecord).where(DetectionRecord.location_id == location.id, DetectionRecord.detected_at > now - WINDOW, DetectionRecord.detected_at <= now, DetectionRecord.status == "low_confidence")).all()
        failed = database.scalars(select(TollTransaction).where(TollTransaction.location_id == location.id, TollTransaction.processed_at > now - WINDOW, TollTransaction.processed_at <= now, TollTransaction.status.in_(("failed", "insufficient_balance")))).all()
        for kind, rows in (("repeated_low_confidence", low), ("repeated_failed_payment", failed)):
            alert = _repeated_failure_rollup(database, location, kind, rows, now)
            if alert:
                alerts.append(alert)
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
    except Exception:  # noqa: BLE001 - Diagnostic persistence must not mask the original failure.
        database.rollback()

def record_recovery(database: Session, component: str, operation: str, *, location_id=None) -> None:
    key = f"failure:{component}:{operation}:{location_id or 'network'}"
    if key not in RUNTIME_HEALTH: return
    RUNTIME_HEALTH.pop(key, None)
    alert = database.scalar(select(OperationalAlert).where(OperationalAlert.incident_key == key))
    if alert:
        alert.status = "resolved"; alert.last_seen_at = datetime.now(UTC)
        record_event(database, event_type=f"{component}_recovered", severity="information", message=f"{component.title()} recovered for {operation}.", location_id=location_id, alert_id=alert.id)

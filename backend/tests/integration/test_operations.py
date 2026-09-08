from sqlalchemy import select
from datetime import UTC, datetime, timedelta

from app.models import OperationalAlert, OperationalEvent, TollLocation
from app.services.operations import RUNTIME_HEALTH, emit, record_failure, record_recovery


def test_backend_failures_are_coalesced_and_sanitized(database) -> None:
    record_failure("backend_api", "GET /api/live/overview", "token=secret\ntrace", database=database)
    record_failure("backend_api", "GET /api/live/overview", "token=secret\ntrace", database=database)
    alerts = list(database.scalars(select(OperationalAlert)))
    assert len(alerts) == 1
    assert alerts[0].severity == "warning"
    assert "secret" not in alerts[0].message
    assert "trace" not in alerts[0].message
    assert len(list(database.scalars(select(OperationalEvent)))) == 1


def test_database_failure_is_critical_and_recovery_is_preserved(database) -> None:
    record_failure("database", "persist toll", "connection unavailable", database=database)
    record_recovery(database, "database", "persist toll")
    database.commit()
    alert = database.scalar(select(OperationalAlert))
    assert alert.severity == "critical"
    assert alert.status == "resolved"
    assert database.scalar(select(OperationalEvent).where(OperationalEvent.event_type == "database_recovered"))


def test_demo_reset_preserves_detected_alerts(database_app, database, admin_auth_headers) -> None:
    from fastapi.testclient import TestClient
    emit(database, alert_type="severe_congestion", severity="critical", title="Real", message="Detected", incident_key="detected:test")
    database.commit(); client = TestClient(database_app)
    assert client.post("/api/operations/alerts/seed-demo", headers=admin_auth_headers).status_code == 200
    assert client.post("/api/operations/alerts/reset-demo", headers=admin_auth_headers).status_code == 200
    assert database.scalar(select(OperationalAlert).where(OperationalAlert.incident_key == "detected:test"))
    assert not database.scalar(select(OperationalAlert).where(OperationalAlert.source == "demo"))


def test_event_filters_are_location_scoped(database_app, database, admin_auth_headers) -> None:
    from fastapi.testclient import TestClient
    locations = list(database.scalars(select(TollLocation).limit(2)))
    if len(locations) < 2:
        return
    from app.services.operations import record_event
    record_event(database, event_type="pricing_change", location_id=locations[0].id, severity="information", message="A")
    record_event(database, event_type="camera_restored", location_id=locations[1].id, severity="information", message="B")
    database.commit(); client = TestClient(database_app)
    response = client.get(f"/api/operations/events?location_id={locations[0].id}&event_type=pricing_change", headers=admin_auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["message"] == "A"


def test_camera_transitions_create_one_outage_and_one_recovery_event(database, monkeypatch) -> None:
    from app.api import locations as locations_api
    from app.services.operations import evaluate
    location = database.scalar(select(TollLocation))
    telemetry = {"congestion_percentage": 10, "camera_status": "offline"}
    monkeypatch.setattr(locations_api, "_state", lambda *_: {"telemetry": telemetry})
    evaluate(database); evaluate(database)
    assert len(list(database.scalars(select(OperationalAlert).where(OperationalAlert.alert_type == "camera_outage", OperationalAlert.location_id == location.id)))) == 1
    assert len(list(database.scalars(select(OperationalEvent).where(OperationalEvent.event_type == "camera_outage", OperationalEvent.location_id == location.id)))) == 1
    telemetry["camera_status"] = "online"; evaluate(database)
    assert database.scalar(select(OperationalEvent).where(OperationalEvent.event_type == "camera_restored"))


def test_alert_and_event_history_filters_preserve_acknowledged_and_resolved(database_app, database, admin_auth_headers) -> None:
    from fastapi.testclient import TestClient
    from app.services.operations import record_event
    location = database.scalar(select(TollLocation))
    alert = emit(database, alert_type="test", severity="warning", title="Test", message="history", location_id=location.id, incident_key="history:test")
    alert.status = "resolved"; alert.acknowledged_at = datetime.now(UTC)
    record_event(database, event_type="test_event", severity="warning", location_id=location.id, source="demo", message="history")
    database.commit(); client = TestClient(database_app)
    alerts = client.get(f"/api/operations/alerts?location_id={location.id}&severity=warning&status=resolved&acknowledged=true", headers=admin_auth_headers)
    events = client.get(f"/api/operations/events?location_id={location.id}&event_type=test_event&severity=warning&source=demo", headers=admin_auth_headers)
    assert len(alerts.json()) == 1 and alerts.json()[0]["status"] == "resolved"
    assert events.status_code == 200 and len(events.json()) == 1 and events.json()[0]["source"] == "demo"


def test_demo_and_acknowledgement_actions_are_events(database_app, database, admin_auth_headers) -> None:
    from fastapi.testclient import TestClient
    client = TestClient(database_app)
    client.post("/api/operations/alerts/seed-demo", headers=admin_auth_headers)
    alert = database.scalar(select(OperationalAlert).where(OperationalAlert.source == "demo"))
    assert client.post(f"/api/operations/alerts/{alert.id}/acknowledge", headers=admin_auth_headers).status_code == 200
    assert client.post("/api/operations/alerts/reset-demo", headers=admin_auth_headers).status_code == 200
    actions = list(database.scalars(select(OperationalEvent).where(OperationalEvent.event_type == "administrator_action")))
    assert {"Demo alerts seeded.", "Administrator acknowledged an operational alert.", "Demo alerts reset."}.issubset({item.message for item in actions})

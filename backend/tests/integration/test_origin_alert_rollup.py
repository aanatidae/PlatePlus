"""Origin rejections enrich one bounded incident, never per-detection alerts."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.api import locations as locations_api
from app.models import DetectionRecord, OperationalAlert, OperationalEvent, TollLocation
from app.services import operations

NOW = datetime(2026, 10, 7, 9, tzinfo=UTC)


def setup_clock(database, monkeypatch):
    class Clock(datetime):
        value = NOW

        @classmethod
        def now(cls, tz=None):
            return cls.value if tz else cls.value.replace(tzinfo=None)

    monkeypatch.setattr(operations, "datetime", Clock)
    monkeypatch.setattr(locations_api, "_state", lambda *_: {"telemetry": {"congestion_percentage": 10, "camera_status": "online"}})
    return Clock, database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))


def reject(database, location, count=1, *, origin=True, when=NOW):
    for _ in range(count):
        database.add(DetectionRecord(location_id=location.id, detected_at=when,
                                     detection_confidence=.99, ocr_confidence=.99 if origin else .1,
                                     status="low_confidence", plate_origin="unknown",
                                     origin_reason="ambiguous_supported_patterns" if origin else "not_evaluated_or_rejected",
                                     source="uploaded_image"))
    database.flush()


def test_origin_rollup_is_thresholded_deduplicated_acknowledgeable_and_recovers(database, monkeypatch):
    clock, location = setup_clock(database, monkeypatch)
    reject(database, location, 2)
    reject(database, location, 3, when=NOW - timedelta(minutes=15))
    reject(database, location, 3, when=NOW + timedelta(seconds=1))
    operations.evaluate(database)
    assert not list(database.scalars(select(OperationalAlert)))
    reject(database, location)
    operations.evaluate(database)
    alert = database.scalar(select(OperationalAlert))
    assert alert.alert_type == "repeated_low_confidence" and alert.severity == "warning"
    assert alert.title == "Repeated plate-origin rejections"
    assert "3 were ambiguous or unsupported" in alert.message
    assert "without a deduction" in alert.message
    identifier = alert.id
    for _ in range(3):
        operations.evaluate(database)
    assert len(list(database.scalars(select(OperationalAlert)))) == 1
    assert len(list(database.scalars(select(OperationalEvent)))) == 1
    # Expected safe pattern rejection does not become critical solely by volume.
    reject(database, location, 3)
    operations.evaluate(database)
    assert alert.severity == "warning"
    alert.status = "acknowledged"
    alert.acknowledged_at = NOW
    database.commit()
    operations.evaluate(database)
    assert alert.status == "acknowledged"
    clock.value = NOW + timedelta(minutes=16)
    operations.evaluate(database)
    operations.evaluate(database)
    assert alert.status == "resolved"
    assert len(list(database.scalars(select(OperationalEvent).where(OperationalEvent.event_type == "repeated_low_confidence_recovered")))) == 1
    reject(database, location, 3, when=clock.value)
    operations.evaluate(database)
    assert alert.id == identifier and alert.status == "active" and alert.acknowledged_at is None
    assert len(list(database.scalars(select(OperationalAlert)))) == 1
    assert database.scalar(select(OperationalEvent).where(OperationalEvent.event_type == "repeated_low_confidence_recurred"))


def test_mixed_failures_escalate_one_incident_only_for_actual_confidence_failures(database, monkeypatch):
    _, location = setup_clock(database, monkeypatch)
    reject(database, location, 3)
    operations.evaluate(database)
    alert = database.scalar(select(OperationalAlert))
    reject(database, location, 5, origin=False)
    operations.evaluate(database)
    operations.evaluate(database)
    assert alert.severity == "critical" and "3 were ambiguous or unsupported" in alert.message
    assert len(list(database.scalars(select(OperationalAlert)))) == 1
    assert len(list(database.scalars(select(OperationalEvent).where(OperationalEvent.event_type == "repeated_low_confidence_severity_changed")))) == 1


def test_origin_counts_are_local_and_retired_locations_never_raise_new_incidents(database, monkeypatch):
    _, location = setup_clock(database, monkeypatch)
    other = database.scalar(select(TollLocation).where(TollLocation.code == "AKLEH"))
    retired = database.scalar(select(TollLocation).where(TollLocation.status == "retired"))
    reject(database, location, 2)
    reject(database, other, 2)
    reject(database, retired, 5)
    operations.evaluate(database)
    assert not list(database.scalars(select(OperationalAlert)))


def test_legacy_severity_incidents_coalesce_without_deleting_history(database, monkeypatch):
    _, location = setup_clock(database, monkeypatch)
    first = operations.emit(database, alert_type="repeated_low_confidence", severity="warning",
                            title="Legacy", message="Legacy", location_id=location.id)
    second = operations.emit(database, alert_type="repeated_low_confidence", severity="critical",
                             title="Legacy", message="Legacy", location_id=location.id)
    database.commit()
    reject(database, location, 3)
    operations.evaluate(database)
    incidents = list(database.scalars(select(OperationalAlert)))
    assert len(incidents) == 2  # Historical rows are retained.
    assert sum(item.status != "resolved" for item in incidents) == 1
    assert {item.id for item in incidents} == {first.id, second.id}

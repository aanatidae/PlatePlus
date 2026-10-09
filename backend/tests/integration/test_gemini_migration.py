from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text


def test_fallback_migration_backfills_and_refuses_lossy_downgrade(test_engine, reset_schema):
    reset_schema("20261007_0014")
    detection_id = str(uuid4())
    with test_engine.begin() as connection:
        location = connection.scalar(text("SELECT id FROM toll_locations WHERE code='SIMULATOR'"))
        connection.execute(text("""INSERT INTO detection_records
            (id,location_id,detected_at,normalized_plate,plate_origin,detection_confidence,status,source)
            VALUES (:id,:location,:now,'VAA1234','malaysian',0.9,'accepted','uploaded_image')"""),
            {"id": detection_id, "location": location, "now": datetime.now(UTC)})
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    with test_engine.begin() as connection:
        record = connection.execute(text("SELECT recognition_source, origin_source, fallback_used, fallback_status FROM detection_records WHERE id=:id"), {"id": detection_id}).one()
        assert tuple(record) == ("local_alpr", "local_rules", False, "not_requested")
        connection.execute(text("UPDATE detection_records SET fallback_used=true WHERE id=:id"), {"id": detection_id})
    columns = {item["name"]: item for item in inspect(test_engine).get_columns("detection_records")}
    assert columns["detection_confidence"]["nullable"]
    with pytest.raises(RuntimeError, match="Cannot downgrade"):
        command.downgrade(config, "20261007_0014")
    reset_schema()  # Disposable test rows only; restore head for subsequent tests.

"""Audit optional external fallback and allow validated other-foreign registrations."""

import sqlalchemy as sa
from alembic import op

revision = "20261009_0015"
down_revision = "20261007_0014"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_vehicles_registration_origin", "vehicles", type_="check")
    op.create_check_constraint("ck_vehicles_registration_origin", "vehicles",
                               "registration_origin IN ('malaysian', 'singaporean', 'foreign_other')")
    op.add_column("vehicles", sa.Column("origin_country", sa.String(64)))
    op.drop_constraint("ck_detection_records_plate_origin", "detection_records", type_="check")
    op.create_check_constraint("ck_detection_records_plate_origin", "detection_records",
                               "plate_origin IN ('malaysian', 'singaporean', 'foreign_other', 'unknown')")
    for name, kind, default in [
        ("recognition_source", sa.String(24), "local_alpr"),
        ("origin_source", sa.String(24), "local_rules"),
        ("fallback_status", sa.String(32), "not_requested"),
        ("fallback_used", sa.Boolean, "false"),
    ]:
        op.add_column("detection_records", sa.Column(name, kind, nullable=False, server_default=default))
    op.add_column("detection_records", sa.Column("origin_country", sa.String(64)))
    op.add_column("detection_records", sa.Column("fallback_provider", sa.String(16)))
    op.alter_column("detection_records", "detection_confidence", existing_type=sa.Numeric(5, 4), nullable=True)


def downgrade():
    # Refuse a lossy downgrade once fallback/other-foreign evidence has been used.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM vehicles WHERE registration_origin = 'foreign_other'")) or connection.scalar(sa.text(
        "SELECT count(*) FROM detection_records WHERE fallback_used OR plate_origin = 'foreign_other' OR fallback_status != 'not_requested'"
    )):
        raise RuntimeError("Cannot downgrade while external fallback/other-foreign audit records exist.")
    op.execute("UPDATE detection_records SET detection_confidence = 0 WHERE detection_confidence IS NULL")
    op.alter_column("detection_records", "detection_confidence", existing_type=sa.Numeric(5, 4), nullable=False)
    for name in ("fallback_provider", "origin_country", "fallback_used", "fallback_status", "origin_source", "recognition_source"):
        op.drop_column("detection_records", name)
    op.drop_constraint("ck_detection_records_plate_origin", "detection_records", type_="check")
    op.create_check_constraint("ck_detection_records_plate_origin", "detection_records", "plate_origin IN ('malaysian', 'singaporean', 'unknown')")
    op.drop_column("vehicles", "origin_country")
    op.drop_constraint("ck_vehicles_registration_origin", "vehicles", type_="check")
    op.create_check_constraint("ck_vehicles_registration_origin", "vehicles", "registration_origin IN ('malaysian', 'singaporean')")

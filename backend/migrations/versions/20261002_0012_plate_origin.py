"""Persist conservative plate-origin classification for ALPR audit."""

import sqlalchemy as sa
from alembic import op

revision = "20261002_0012"
down_revision = "20260908_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical OCR results have not passed the V3 classifier. Do not infer
    # their origin retroactively from a plate string alone.
    op.add_column(
        "detection_records",
        sa.Column("plate_origin", sa.String(16), nullable=False, server_default="unknown"),
    )
    op.add_column("detection_records", sa.Column("origin_reason", sa.String(64)))
    op.create_check_constraint(
        "ck_detection_records_plate_origin",
        "detection_records",
        "plate_origin IN ('malaysian', 'singaporean', 'unknown')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_detection_records_plate_origin", "detection_records", type_="check")
    op.drop_column("detection_records", "origin_reason")
    op.drop_column("detection_records", "plate_origin")

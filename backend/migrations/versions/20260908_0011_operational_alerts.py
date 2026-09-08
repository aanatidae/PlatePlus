"""Add deduplicated operational alerts and append-only event history."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260908_0011"
down_revision = "20260908_0010"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("operational_alerts", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("toll_locations.id", ondelete="SET NULL")), sa.Column("alert_type", sa.String(64), nullable=False), sa.Column("severity", sa.String(16), nullable=False), sa.Column("status", sa.String(16), nullable=False, server_default="active"), sa.Column("title", sa.String(160), nullable=False), sa.Column("message", sa.String(500), nullable=False), sa.Column("source", sa.String(16), nullable=False, server_default="detected"), sa.Column("incident_key", sa.String(180), nullable=False, unique=True), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False), sa.Column("acknowledged_at", sa.DateTime(timezone=True)), sa.Column("acknowledged_by_admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admins.id", ondelete="SET NULL")), sa.Column("metadata_json", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    for column in ("location_id", "alert_type", "severity", "status", "started_at"): op.create_index(f"ix_operational_alerts_{column}", "operational_alerts", [column])
    op.create_table("operational_events", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("toll_locations.id", ondelete="SET NULL")), sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operational_alerts.id", ondelete="SET NULL")), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("severity", sa.String(16), nullable=False, server_default="information"), sa.Column("source", sa.String(16), nullable=False, server_default="detected"), sa.Column("message", sa.String(500), nullable=False), sa.Column("details_json", sa.Text()), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    for column in ("location_id", "alert_id", "event_type", "severity", "occurred_at"): op.create_index(f"ix_operational_events_{column}", "operational_events", [column])

def downgrade() -> None:
    for table, columns in (("operational_events", ("occurred_at", "severity", "event_type", "alert_id", "location_id")), ("operational_alerts", ("started_at", "status", "severity", "alert_type", "location_id"))):
        for column in columns: op.drop_index(f"ix_{table}_{column}", table_name=table)
    op.drop_table("operational_events")
    op.drop_table("operational_alerts")

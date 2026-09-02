"""Add configurable traffic simulation, pricing rules, and audit history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260902_0003"
down_revision = "20260902_0002"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")


def upgrade() -> None:
    op.add_column("traffic_records", sa.Column("source", sa.String(16), nullable=False, server_default="manual"))
    op.add_column("traffic_records", sa.Column("simulation_mode", sa.String(32), nullable=False, server_default="manual"))
    op.add_column("traffic_records", sa.Column("simulation_time", sa.DateTime(timezone=True)))

    op.create_table(
        "traffic_simulation_settings",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("singleton_key", sa.String(32), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("simulation_mode", sa.String(32), nullable=False, server_default="time_patterned"),
        sa.Column("fixed_scenario", sa.String(32), nullable=False, server_default="moderate"),
        sa.Column("time_mode", sa.String(16), nullable=False, server_default="real"),
        sa.Column("simulated_time", sa.DateTime(timezone=True)),
        sa.Column("simulated_time_anchor", sa.DateTime(timezone=True)),
        sa.Column("pricing_rule_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint("singleton_key", name="uq_traffic_simulation_settings_key"),
        sa.CheckConstraint("interval_minutes IN (1, 5, 15)", name="ck_simulation_interval"),
        sa.CheckConstraint("simulation_mode IN ('time_patterned', 'fixed_scenario')", name="ck_simulation_mode"),
        sa.CheckConstraint("fixed_scenario IN ('normal', 'moderate', 'peak_hour', 'severe')", name="ck_simulation_fixed_scenario"),
        sa.CheckConstraint("time_mode IN ('real', 'simulated')", name="ck_simulation_time_mode"),
    )
    op.create_table(
        "dynamic_pricing_rules",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scenario", sa.String(32), nullable=False),
        sa.Column("congestion_category", sa.String(16), nullable=False),
        sa.Column("minimum_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("maximum_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("amount", sa.Numeric(8, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint("scenario", name="uq_dynamic_pricing_rules_scenario"),
        sa.CheckConstraint("minimum_percentage >= 0", name="ck_pricing_rule_minimum"),
        sa.CheckConstraint("maximum_percentage <= 100", name="ck_pricing_rule_maximum"),
        sa.CheckConstraint("minimum_percentage <= maximum_percentage", name="ck_pricing_rule_order"),
        sa.CheckConstraint("amount >= 0", name="ck_pricing_rule_amount"),
    )
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("admin_id", UUID, sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_admin_audit_logs_admin_id", "admin_audit_logs", ["admin_id"])
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"])
    op.bulk_insert(
        sa.table("traffic_simulation_settings", sa.column("singleton_key")), [{"singleton_key": "default"}]
    )
    rules = sa.table(
        "dynamic_pricing_rules", sa.column("scenario"), sa.column("congestion_category"),
        sa.column("minimum_percentage"), sa.column("maximum_percentage"), sa.column("amount"),
    )
    op.bulk_insert(rules, [
        {"scenario": "normal", "congestion_category": "low", "minimum_percentage": 0, "maximum_percentage": 30, "amount": 2},
        {"scenario": "moderate", "congestion_category": "moderate", "minimum_percentage": 30.01, "maximum_percentage": 60, "amount": 3},
        {"scenario": "peak_hour", "congestion_category": "high", "minimum_percentage": 60.01, "maximum_percentage": 80, "amount": 4},
        {"scenario": "severe", "congestion_category": "severe", "minimum_percentage": 80.01, "maximum_percentage": 100, "amount": 5},
    ])


def downgrade() -> None:
    op.drop_table("admin_audit_logs")
    op.drop_table("dynamic_pricing_rules")
    op.drop_table("traffic_simulation_settings")
    op.drop_column("traffic_records", "simulation_time")
    op.drop_column("traffic_records", "simulation_mode")
    op.drop_column("traffic_records", "source")

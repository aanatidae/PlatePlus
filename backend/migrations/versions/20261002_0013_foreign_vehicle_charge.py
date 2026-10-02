"""Add synthetic Singaporean registration and itemized foreign-charge support."""

import sqlalchemy as sa
from alembic import op

revision = "20261002_0013"
down_revision = "20261002_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("registration_origin", sa.String(16), nullable=False, server_default="malaysian"))
    op.create_check_constraint(
        "ck_vehicles_registration_origin", "vehicles",
        "registration_origin IN ('malaysian', 'singaporean')",
    )
    op.add_column("toll_transactions", sa.Column("dynamic_toll_amount", sa.Numeric(8, 2), nullable=False, server_default="0.00"))
    op.add_column("toll_transactions", sa.Column("foreign_vehicle_charge", sa.Numeric(8, 2), nullable=False, server_default="0.00"))
    op.execute("UPDATE toll_transactions SET dynamic_toll_amount = amount")
    op.create_check_constraint("ck_transactions_dynamic_toll_nonnegative", "toll_transactions", "dynamic_toll_amount >= 0")
    op.create_check_constraint("ck_transactions_foreign_charge_nonnegative", "toll_transactions", "foreign_vehicle_charge >= 0")
    op.create_table(
        "foreign_vehicle_charge_settings",
        sa.Column("singleton_key", sa.String(32), primary_key=True),
        sa.Column("amount", sa.Numeric(8, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount >= 0", name="ck_foreign_vehicle_charge_nonnegative"),
    )
    op.execute("INSERT INTO foreign_vehicle_charge_settings (singleton_key, amount) VALUES ('default', 20.00)")


def downgrade() -> None:
    op.drop_table("foreign_vehicle_charge_settings")
    op.drop_constraint("ck_transactions_foreign_charge_nonnegative", "toll_transactions", type_="check")
    op.drop_constraint("ck_transactions_dynamic_toll_nonnegative", "toll_transactions", type_="check")
    op.drop_column("toll_transactions", "foreign_vehicle_charge")
    op.drop_column("toll_transactions", "dynamic_toll_amount")
    op.drop_constraint("ck_vehicles_registration_origin", "vehicles", type_="check")
    op.drop_column("vehicles", "registration_origin")

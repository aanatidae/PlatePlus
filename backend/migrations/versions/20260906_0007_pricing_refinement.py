"""Location-aware pricing multipliers and stability safeguards."""
import sqlalchemy as sa
from alembic import op

revision = "20260906_0007"
down_revision = "20260905_0006"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("traffic_simulation_settings", sa.Column("minimum_toll", sa.Numeric(8, 2), nullable=False, server_default="0.50"))
    op.add_column("traffic_simulation_settings", sa.Column("maximum_toll_multiplier", sa.Numeric(5, 2), nullable=False, server_default="3.00"))
    op.add_column("traffic_simulation_settings", sa.Column("minimum_price_change_minutes", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("traffic_simulation_settings", sa.Column("pricing_hysteresis_percentage", sa.Numeric(5, 2), nullable=False, server_default="2.00"))
    op.add_column("dynamic_pricing_rules", sa.Column("multiplier", sa.Numeric(5, 2), nullable=False, server_default="1.00"))
    rules = sa.table("dynamic_pricing_rules", sa.column("scenario"), sa.column("multiplier"))
    for scenario, multiplier in (("normal", 1), ("moderate", 1.5), ("peak_hour", 2), ("severe", 2.5)):
        op.execute(rules.update().where(rules.c.scenario == scenario).values(multiplier=multiplier))

def downgrade() -> None:
    op.drop_column("dynamic_pricing_rules", "multiplier")
    for column in ("pricing_hysteresis_percentage", "minimum_price_change_minutes", "maximum_toll_multiplier", "minimum_toll"):
        op.drop_column("traffic_simulation_settings", column)

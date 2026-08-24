"""Make company identity deterministic for nullable countries."""

import sqlalchemy as sa
from alembic import op

revision = "0012_company_identity"
down_revision = "0011_candidate_security_and_freshness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch:
        batch.add_column(
            sa.Column("country_key", sa.String(length=100), nullable=False, server_default="")
        )
    op.execute("UPDATE companies SET country_key = COALESCE(country, '')")
    with op.batch_alter_table("companies") as batch:
        batch.drop_constraint("uq_company_name_country", type_="unique")
        batch.create_unique_constraint(
            "uq_company_name_country_key", ["normalized_name", "country_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("companies") as batch:
        batch.drop_constraint("uq_company_name_country_key", type_="unique")
        batch.create_unique_constraint("uq_company_name_country", ["normalized_name", "country"])
        batch.drop_column("country_key")

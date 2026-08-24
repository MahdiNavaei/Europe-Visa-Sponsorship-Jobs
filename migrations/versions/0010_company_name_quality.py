"""Track whether a company display name is a trustworthy employer identity."""

import sqlalchemy as sa
from alembic import op

revision = "0010_company_name_quality"
down_revision = "0009_product_truth_semantics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("name_quality", sa.String(length=20), nullable=False, server_default="verified"))
    op.create_index("ix_companies_name_quality", "companies", ["name_quality"])


def downgrade() -> None:
    op.drop_index("ix_companies_name_quality", table_name="companies")
    op.drop_column("companies", "name_quality")

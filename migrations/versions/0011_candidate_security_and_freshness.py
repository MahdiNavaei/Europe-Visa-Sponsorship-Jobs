"""Protect candidate records and persist eligibility assessment freshness."""

import sqlalchemy as sa
from alembic import op

revision = "0011_candidate_security_and_freshness"
down_revision = "0010_company_name_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidates", sa.Column("access_token_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_candidates_access_token_hash", "candidates", ["access_token_hash"])
    op.add_column("jobs", sa.Column("eligibility_assessed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "eligibility_assessed_at")
    op.drop_index("ix_candidates_access_token_hash", table_name="candidates")
    op.drop_column("candidates", "access_token_hash")

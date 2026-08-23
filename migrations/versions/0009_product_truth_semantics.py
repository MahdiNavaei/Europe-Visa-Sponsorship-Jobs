"""Persist catalog accounting and independent sponsorship semantics."""

import sqlalchemy as sa
from alembic import op

revision = "0009_product_truth_semantics"
down_revision = "0008_incremental_source_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("classification_status", sa.String(length=30), nullable=False, server_default="classification_unknown"))
    op.add_column("jobs", sa.Column("job_sponsorship_signal", sa.String(length=30), nullable=False, server_default="not_mentioned"))
    op.add_column("jobs", sa.Column("company_sponsor_status", sa.String(length=30), nullable=False, server_default="unresolved"))
    op.add_column("jobs", sa.Column("final_candidate_eligibility", sa.String(length=30), nullable=False, server_default="unknown"))
    op.create_index("ix_jobs_classification_status", "jobs", ["classification_status"])
    op.create_index("ix_jobs_job_sponsorship_signal", "jobs", ["job_sponsorship_signal"])
    op.create_index("ix_jobs_company_sponsor_status", "jobs", ["company_sponsor_status"])
    op.create_index("ix_jobs_final_candidate_eligibility", "jobs", ["final_candidate_eligibility"])


def downgrade() -> None:
    for name in ("ix_jobs_final_candidate_eligibility", "ix_jobs_company_sponsor_status", "ix_jobs_job_sponsorship_signal", "ix_jobs_classification_status"):
        op.drop_index(name, table_name="jobs")
    for name in ("final_candidate_eligibility", "company_sponsor_status", "job_sponsorship_signal", "classification_status"):
        op.drop_column("jobs", name)

"""Add nullable job deduplication columns used by newer packaged runtimes.

This keeps upgrades from the v1.0.0 Phase 4 schema forward-compatible with
runtime code that can normalize apply URLs and identify cross-source copies.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_runtime_compatibility"
down_revision: Union[str, None] = "0003_candidate_job_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("canonical_apply_url", sa.String(length=1000), nullable=True))
    op.add_column("jobs", sa.Column("duplicate_of_job_id", sa.Integer(), nullable=True))
    op.create_index("ix_jobs_canonical_apply_url", "jobs", ["canonical_apply_url"], unique=False)
    op.create_index("ix_jobs_duplicate_of_job_id", "jobs", ["duplicate_of_job_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_jobs_duplicate_of_job_id", table_name="jobs")
    op.drop_index("ix_jobs_canonical_apply_url", table_name="jobs")
    op.drop_column("jobs", "duplicate_of_job_id")
    op.drop_column("jobs", "canonical_apply_url")

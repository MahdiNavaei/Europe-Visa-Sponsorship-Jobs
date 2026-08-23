"""Track strong cross-source duplicate signals.

Revision ID: 0005_cross_source_dedup
Revises: 0004_source_registry
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_cross_source_dedup"
down_revision = "0004_source_registry"
branch_labels = None
depends_on = None


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

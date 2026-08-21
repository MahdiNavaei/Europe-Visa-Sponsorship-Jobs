"""Saved jobs and candidate application state.

Revision ID: 0003_candidate_job_tracking
Revises: 0002_phase2_candidate_intelligence
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_candidate_job_tracking"
down_revision = "0002_phase2_candidate_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_job_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saved", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("application_status", sa.String(length=30), nullable=False, server_default="not_applied"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job_state"),
    )
    op.create_index("ix_candidate_job_states_candidate_id", "candidate_job_states", ["candidate_id"])
    op.create_index("ix_candidate_job_states_job_id", "candidate_job_states", ["job_id"])
    op.create_index("ix_candidate_job_states_application_status", "candidate_job_states", ["application_status"])


def downgrade() -> None:
    op.drop_index("ix_candidate_job_states_application_status", table_name="candidate_job_states")
    op.drop_index("ix_candidate_job_states_job_id", table_name="candidate_job_states")
    op.drop_index("ix_candidate_job_states_candidate_id", table_name="candidate_job_states")
    op.drop_table("candidate_job_states")

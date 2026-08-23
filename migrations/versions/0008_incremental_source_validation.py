"""Add durable source validation state and incremental retry accounting."""

from alembic import op
import sqlalchemy as sa


revision = "0008_incremental_source_validation"
down_revision = "0007_source_query_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("validation_state", sa.String(length=30), nullable=False, server_default="discovered"))
    op.add_column("sources", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sources", sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sources", sa.Column("failure_type", sa.String(length=80), nullable=True))
    op.add_column("sources", sa.Column("validation_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_sources_validation_state_retry_after", "sources", ["validation_state", "retry_after"])

    op.add_column("discovery_runs", sa.Column("candidate_before_filter_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("discovery_runs", sa.Column("candidate_after_filter_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("discovery_runs", sa.Column("skipped_cached_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("discovery_runs", sa.Column("failure_breakdown", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("discovery_runs", sa.Column("provider_failure_breakdown", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    op.drop_column("discovery_runs", "provider_failure_breakdown")
    op.drop_column("discovery_runs", "failure_breakdown")
    op.drop_column("discovery_runs", "skipped_cached_count")
    op.drop_column("discovery_runs", "candidate_after_filter_count")
    op.drop_column("discovery_runs", "candidate_before_filter_count")
    op.drop_index("ix_sources_validation_state_retry_after", table_name="sources")
    op.drop_column("sources", "validation_attempts")
    op.drop_column("sources", "failure_type")
    op.drop_column("sources", "retry_after")
    op.drop_column("sources", "last_checked_at")
    op.drop_column("sources", "validation_state")

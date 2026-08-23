"""Persistent discovered source registry and health history."""

from alembic import op
import sqlalchemy as sa

revision = "0004_source_registry"
down_revision = "0003_candidate_job_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("normalized_company_name", sa.String(length=255), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("board_identifier", sa.String(length=255), nullable=False),
        sa.Column("careers_url", sa.Text(), nullable=True),
        sa.Column("board_url", sa.Text(), nullable=True),
        sa.Column("api_url", sa.Text(), nullable=True),
        sa.Column("country_hint", sa.String(length=100), nullable=True),
        sa.Column("discovery_method", sa.String(length=80), nullable=False, server_default="manual_seed"),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_job_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("technical_job_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_job_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eligible_job_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unknown_job_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_job_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="unverified"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("manual_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_http_status", sa.Integer(), nullable=True),
        sa.Column("last_error_category", sa.String(length=80), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("etag", sa.String(length=500), nullable=True),
        sa.Column("last_modified", sa.String(length=255), nullable=True),
        sa.Column("last_fetch_duration_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.UniqueConstraint("provider", "board_identifier", name="uq_source_provider_board"),
    )
    for name, columns in (
        ("ix_sources_normalized_company_name", ["normalized_company_name"]),
        ("ix_sources_provider", ["provider"]),
        ("ix_sources_country_hint", ["country_hint"]),
        ("ix_sources_status", ["status"]),
        ("ix_sources_enabled", ["enabled"]),
        ("ix_sources_status_enabled", ["status", "enabled"]),
        ("ix_sources_provider_status", ["provider", "status"]),
    ):
        op.create_index(name, "sources", columns)

    op.create_table(
        "discovery_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mode", sa.String(length=30), nullable=False),
        sa.Column("methods", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_counts", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error", sa.Text(), nullable=True),
    )

    op.create_table(
        "source_health_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("discovery_run_id", sa.Integer(), sa.ForeignKey("discovery_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_category", sa.String(length=80), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("raw_job_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_source_health_events_source_id", "source_health_events", ["source_id"])
    op.create_index("ix_source_health_events_source_observed", "source_health_events", ["source_id", "observed_at"])


def downgrade() -> None:
    op.drop_table("source_health_events")
    op.drop_table("discovery_runs")
    op.drop_table("sources")

"""Phase 1 core schema.

Revision ID: 0001_phase1_core
Revises: None
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_phase1_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("career_url", sa.Text(), nullable=True),
        sa.Column("sponsor_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("normalized_name", "country", name="uq_company_name_country"),
    )
    op.create_index("ix_companies_normalized_name", "companies", ["normalized_name"])
    op.create_index("ix_companies_country", "companies", ["country"])

    op.create_table(
        "sponsor_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("registry_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("normalized_name", "country", "registry_name", name="uq_sponsor_record"),
    )
    op.create_index("ix_sponsor_records_normalized_name", "sponsor_records", ["normalized_name"])
    op.create_index("ix_sponsor_records_country", "sponsor_records", ["country"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("source_slug", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("workplace_type", sa.String(length=100), nullable=True),
        sa.Column("apply_url", sa.Text(), nullable=False),
        sa.Column("job_url", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("job_family", sa.String(length=100), nullable=False),
        sa.Column("eligibility_status", sa.String(length=50), nullable=True),
        sa.Column("eligibility_score", sa.Integer(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("provider", "source_slug", "external_id", name="uq_job_source_external"),
    )
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])
    op.create_index("ix_jobs_provider", "jobs", ["provider"])
    op.create_index("ix_jobs_title", "jobs", ["title"])
    op.create_index("ix_jobs_country", "jobs", ["country"])
    op.create_index("ix_jobs_job_family", "jobs", ["job_family"])
    op.create_index("ix_jobs_eligibility_status", "jobs", ["eligibility_status"])
    op.create_index("ix_jobs_active", "jobs", ["active"])
    op.create_index("ix_jobs_country_eligibility", "jobs", ["country", "eligibility_status"])

    op.create_table(
        "job_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("matched_text", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_evidence_job_id", "job_evidence", ["job_id"])
    op.create_index("ix_job_evidence_code", "job_evidence", ["code"])

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("source_slug", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stored_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_ingestion_runs_provider", "ingestion_runs", ["provider"])
    op.create_index("ix_ingestion_runs_source_slug", "ingestion_runs", ["source_slug"])


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("job_evidence")
    op.drop_table("jobs")
    op.drop_table("sponsor_records")
    op.drop_table("companies")

"""Candidate intelligence and persisted job profile fields.

Revision ID: 0002_phase2_candidate_intelligence
Revises: 0001_phase1_core
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_phase2_candidate_intelligence"
down_revision = "0001_phase1_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("years_of_experience", sa.Float(), nullable=False, server_default="0"),
        sa.Column("seniority", sa.String(length=50), nullable=True),
        sa.Column("preferred_countries", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("visa_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("relocation_preference", sa.String(length=30), nullable=False, server_default="preferred"),
        sa.Column("remote_preference", sa.String(length=30), nullable=False, server_default="no_preference"),
        sa.Column("excluded_locations", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("jobs", sa.Column("required_skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("jobs", sa.Column("preferred_skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("jobs", sa.Column("min_experience_years", sa.Float(), nullable=True))
    op.add_column("jobs", sa.Column("seniority", sa.String(length=50), nullable=True))
    op.create_index("ix_jobs_seniority", "jobs", ["seniority"])


def downgrade() -> None:
    op.drop_index("ix_jobs_seniority", table_name="jobs")
    op.drop_column("jobs", "seniority")
    op.drop_column("jobs", "min_experience_years")
    op.drop_column("jobs", "preferred_skills")
    op.drop_column("jobs", "required_skills")
    op.drop_table("candidates")

"""Add composite indexes for registry and health queries.

Revision ID: 0006_source_query_indexes
Revises: 0005_cross_source_dedup
"""

from alembic import op


revision = "0006_source_query_indexes"
down_revision = "0005_cross_source_dedup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_sources_enabled_verified_provider_board",
        "sources",
        ["enabled", "verified_at", "provider", "board_identifier"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sources_enabled_verified_provider_board", table_name="sources")

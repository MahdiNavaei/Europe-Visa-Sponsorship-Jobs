"""Track strong cross-source duplicate signals.

Revision ID: 0006_cross_source_dedup
Revises: 0005_source_registry
"""

revision = "0006_cross_source_dedup"
down_revision = "0005_source_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Current main's 0004_runtime_compatibility migration already owns these
    # columns and indexes. Keep this revision as a graph marker when the
    # scalable-discovery branch is reconciled onto that history.
    pass


def downgrade() -> None:
    pass

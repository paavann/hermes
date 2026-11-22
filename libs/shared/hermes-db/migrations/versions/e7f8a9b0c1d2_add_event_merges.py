"""add event merges and redirect fields

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-11-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e7f8a9b0c1d2"
down_revision: str | Sequence[str] | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add redirect fields and the merged event status."""
    # ALTER TYPE ... ADD VALUE cannot run inside the migration transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE eventstatus ADD VALUE IF NOT EXISTS 'MERGED'")

    op.add_column("events", sa.Column("merged_into_id", sa.Uuid(), nullable=True))
    op.add_column(
        "events",
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("events", sa.Column("merge_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "events_merged_into_id_fkey",
        "events",
        "events",
        ["merged_into_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_events_merge_candidates",
        "events",
        ["country_code", "event_time"],
        postgresql_where=sa.text(
            "merged_into_id IS NULL AND status IN ('ACTIVE', 'STALE')"
        ),
    )


def downgrade() -> None:
    """Remove redirect fields. The merged enum value is left in place."""
    op.drop_index("idx_events_merge_candidates", table_name="events")
    op.drop_constraint("events_merged_into_id_fkey", "events", type_="foreignkey")
    op.drop_column("events", "merge_reason")
    op.drop_column("events", "merged_at")
    op.drop_column("events", "merged_into_id")

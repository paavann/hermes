"""add thread embeddings and counters

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-11-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import HALFVEC


revision: str = "d6e7f8a9b0c1"
down_revision: str | Sequence[str] | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ANN-addressable thread centroids and activity counters."""
    op.add_column(
        "threads",
        sa.Column("name_norm", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "threads",
        sa.Column("event_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "threads",
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "threads",
        sa.Column("embedding", HALFVEC(2048), nullable=True),
    )
    op.add_column(
        "threads",
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
    )
    op.create_index("idx_threads_name_norm", "threads", ["name_norm"])
    op.create_index(
        "idx_threads_status_last_event",
        "threads",
        ["status", "last_event_at"],
    )
    op.create_index(
        "idx_threads_embedding",
        "threads",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "halfvec_cosine_ops"},
    )


def downgrade() -> None:
    """Remove thread embeddings and counters."""
    op.drop_index("idx_threads_embedding", table_name="threads")
    op.drop_index("idx_threads_status_last_event", table_name="threads")
    op.drop_index("idx_threads_name_norm", table_name="threads")
    op.drop_column("threads", "embedding_model")
    op.drop_column("threads", "embedding")
    op.drop_column("threads", "last_event_at")
    op.drop_column("threads", "event_count")
    op.drop_column("threads", "name_norm")

"""remove legacy ranking and body columns

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-11-19 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op


revision: str = "f8a9b0c1d2e3"
down_revision: str | Sequence[str] | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop columns superseded by the single importance score and ledger."""
    op.execute("DROP INDEX IF EXISTS idx_events_active_score")
    op.drop_column("events", "trending_score")
    op.drop_column("events", "popularity_score")
    op.drop_column("events", "velocity")
    op.drop_column("events", "confidence")
    op.drop_column("threads", "confidence")
    op.drop_column("articles", "feed_content")


def downgrade() -> None:
    """Restore the legacy columns as nullable defaults for rollback."""
    import sqlalchemy as sa

    op.add_column(
        "articles",
        sa.Column("feed_content", sa.Text(), nullable=True),
    )
    op.add_column(
        "threads",
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=True,
        ),
    )
    op.add_column(
        "events",
        sa.Column("velocity", sa.Float(), server_default="1.0", nullable=False),
    )
    op.add_column(
        "events",
        sa.Column(
            "popularity_score",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "trending_score",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_index(
        "idx_events_active_score",
        "events",
        ["trending_score"],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

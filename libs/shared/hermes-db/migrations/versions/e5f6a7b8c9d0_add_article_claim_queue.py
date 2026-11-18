"""add article claim queue

Revision ID: e5f6a7b8c9d0
Revises: d5e6f7a8b9c0
Create Date: 2026-11-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INGEST_STATUS_VALUES = (
    "NEW",
    "NORMALIZED",
    "ANALYZING",
    "LABELED",
    "CLUSTERED",
    "REJECTED",
    "FAILED",
)


def _ingest_status_check(values: Sequence[str]) -> str:
    joined = ", ".join(f"'{value}'" for value in values)
    return f"ingest_status IN ({joined})"


def upgrade() -> None:
    """Add the article claim queue fields used by worker stages."""
    op.add_column(
        "articles",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("claimed_by", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column("articles", sa.Column("last_error", sa.Text(), nullable=True))
    op.create_index(
        "idx_articles_analyzing_claimed_at",
        "articles",
        ["claimed_at"],
        postgresql_where=sa.text("ingest_status = 'ANALYZING'"),
    )

    # native_enum=False stores the allowed values in a check constraint named
    # after the enum type. Earlier revisions never created that constraint, so
    # drop it if a previous database happens to have it and replace it.
    op.execute("ALTER TABLE articles DROP CONSTRAINT IF EXISTS ingeststatus")
    op.create_check_constraint(
        "ingeststatus",
        "articles",
        _ingest_status_check(INGEST_STATUS_VALUES),
    )


def downgrade() -> None:
    """Remove the article claim queue fields."""
    op.execute("ALTER TABLE articles DROP CONSTRAINT IF EXISTS ingeststatus")
    op.execute(
        "UPDATE articles SET ingest_status = 'NEW' "
        "WHERE ingest_status IN ('ANALYZING', 'FAILED')"
    )

    op.drop_index("idx_articles_analyzing_claimed_at", table_name="articles")
    op.drop_column("articles", "last_error")
    op.drop_column("articles", "attempt_count")
    op.drop_column("articles", "claimed_by")
    op.drop_column("articles", "claimed_at")

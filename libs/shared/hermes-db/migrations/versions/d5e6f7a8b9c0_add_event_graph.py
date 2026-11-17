"""add event graph, threads, and source health fields

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-11-17 00:00:01.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SELECTION_TIER = sa.Enum(
    "PRIMARY", "FILLER", "DROP", name="selectiontier", native_enum=False
)
VERIFICATION_STATUS = sa.Enum(
    "CONFIRMED",
    "SINGLE_SOURCE",
    "UNVERIFIED",
    name="verificationstatus",
    native_enum=False,
)
THREAD_KIND = sa.Enum("DEVELOPING", "TOPIC", name="threadkind", native_enum=False)
THREAD_STATUS = sa.Enum(
    "ACTIVE", "DORMANT", "ENDED", name="threadstatus", native_enum=False
)


def upgrade() -> None:
    """Add the event graph, thread container, and source health fields."""
    op.create_table(
        "threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            THREAD_KIND,
            server_default="DEVELOPING",
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            THREAD_STATUS,
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "entities",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("importance", sa.Float(), server_default="0", nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_threads_status_importance",
        "threads",
        ["status", "importance"],
    )
    op.create_index("idx_threads_kind_status", "threads", ["kind", "status"])

    op.add_column(
        "events",
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("latest_published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("events", sa.Column("thread_id", sa.Uuid(), nullable=True))
    op.add_column("events", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column(
        "events",
        sa.Column("importance_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "events",
        sa.Column("popularity_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "events",
        sa.Column(
            "selection_tier",
            SELECTION_TIER,
            server_default="DROP",
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "verification_status",
            VERIFICATION_STATUS,
            server_default="UNVERIFIED",
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "independent_origin_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column("member_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_foreign_key(
        "events_thread_id_fkey",
        "events",
        "threads",
        ["thread_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_events_thread_id",
        "events",
        ["thread_id"],
        postgresql_where=sa.text("thread_id IS NOT NULL"),
    )
    op.create_index("idx_events_event_time", "events", ["event_time"])
    op.create_index(
        "idx_events_latest_published_at",
        "events",
        ["latest_published_at"],
    )
    op.create_index(
        "idx_events_active_selection",
        "events",
        ["selection_tier", "importance_score"],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.add_column(
        "sources",
        sa.Column("origin_group", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("country_code", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("language", sa.String(length=16), nullable=True),
    )
    op.add_column("sources", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column(
        "sources",
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_index(
        "idx_sources_origin_group",
        "sources",
        ["origin_group"],
        postgresql_where=sa.text("origin_group IS NOT NULL"),
    )

    # Legacy membership becomes nullable and loses the destructive cascade.
    op.drop_constraint("articles_event_id_fkey", "articles", type_="foreignkey")
    op.alter_column(
        "articles",
        "event_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.create_foreign_key(
        "articles_event_id_fkey",
        "articles",
        "events",
        ["event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_articles_event_id", "articles", ["event_id"])

    # Deleting a source must not delete its ledger articles.
    op.drop_constraint("articles_source_id_fkey", "articles", type_="foreignkey")
    op.alter_column(
        "articles",
        "source_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.create_foreign_key(
        "articles_source_id_fkey",
        "articles",
        "sources",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_articles_source_id", "articles", ["source_id"])

    op.add_column("article_labels", sa.Column("fact", sa.Text(), nullable=True))
    op.add_column(
        "article_labels",
        sa.Column(
            "scale_facts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove the event graph, thread container, and source health fields."""
    op.drop_column("article_labels", "scale_facts")
    op.drop_column("article_labels", "fact")

    op.drop_index("idx_articles_source_id", table_name="articles")
    op.drop_constraint("articles_source_id_fkey", "articles", type_="foreignkey")
    op.alter_column(
        "articles",
        "source_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_foreign_key(
        "articles_source_id_fkey",
        "articles",
        "sources",
        ["source_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("idx_articles_event_id", table_name="articles")
    op.drop_constraint("articles_event_id_fkey", "articles", type_="foreignkey")
    op.alter_column(
        "articles",
        "event_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_foreign_key(
        "articles_event_id_fkey",
        "articles",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("idx_sources_origin_group", table_name="sources")
    op.drop_column("sources", "consecutive_failures")
    op.drop_column("sources", "last_error")
    op.drop_column("sources", "language")
    op.drop_column("sources", "country_code")
    op.drop_column("sources", "origin_group")

    op.drop_index("idx_events_active_selection", table_name="events")
    op.drop_index("idx_events_latest_published_at", table_name="events")
    op.drop_index("idx_events_event_time", table_name="events")
    op.drop_index("idx_events_thread_id", table_name="events")
    op.drop_constraint("events_thread_id_fkey", "events", type_="foreignkey")

    op.drop_column("events", "version")
    op.drop_column("events", "member_hash")
    op.drop_column("events", "independent_origin_count")
    op.drop_column("events", "verification_status")
    op.drop_column("events", "selection_tier")
    op.drop_column("events", "popularity_score")
    op.drop_column("events", "importance_score")
    op.drop_column("events", "confidence")
    op.drop_column("events", "thread_id")
    op.drop_column("events", "latest_published_at")
    op.drop_column("events", "event_time")

    op.drop_index("idx_threads_kind_status", table_name="threads")
    op.drop_index("idx_threads_status_importance", table_name="threads")
    op.drop_table("threads")

"""add article ledger, labels, and embeddings

Revision ID: c4d5e6f7a8b9
Revises: 9e1bb45d1cba
Create Date: 2026-11-17 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "9e1bb45d1cba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INGEST_STATUS = sa.Enum(
    "NEW",
    "NORMALIZED",
    "LABELED",
    "CLUSTERED",
    "REJECTED",
    name="ingeststatus",
    native_enum=False,
)
ARTICLE_TYPE = sa.Enum(
    "BREAKING",
    "DEVELOPMENT",
    "ANALYSIS",
    "FEATURE",
    "OPINION",
    "LISTICLE",
    "OTHER",
    name="articletype",
    native_enum=False,
)
ARTICLE_LABEL_SCOPE = sa.Enum(
    "GLOBAL",
    "COUNTRY",
    "STATE",
    "CITY",
    "LOCAL",
    name="articlelabelscope",
    native_enum=False,
)


def upgrade() -> None:
    """Add the article ledger, LLM labels, and article embeddings."""
    op.add_column("articles", sa.Column("canonical_url", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("feed_summary", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("feed_content", sa.Text(), nullable=True))
    op.add_column(
        "articles", sa.Column("content_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "articles", sa.Column("title_simhash", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "articles", sa.Column("language", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "articles",
        sa.Column(
            "ingest_status",
            INGEST_STATUS,
            server_default="NEW",
            nullable=False,
        ),
    )

    op.create_index("idx_articles_content_hash", "articles", ["content_hash"])
    op.create_index("idx_articles_canonical_url", "articles", ["canonical_url"])
    op.create_index(
        "idx_articles_ingest_status_published_at",
        "articles",
        ["ingest_status", "published_at"],
    )

    # Existing articles are already attached to events, so mark them clustered
    # instead of leaving every historical row at the NEW default.
    op.execute(
        "UPDATE articles SET ingest_status = 'CLUSTERED' "
        "WHERE event_id IS NOT NULL"
    )

    op.create_table(
        "article_labels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("is_event", sa.Boolean(), nullable=False),
        sa.Column(
            "article_type",
            ARTICLE_TYPE,
            server_default="OTHER",
            nullable=False,
        ),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("severity", sa.SmallInteger(), nullable=True),
        sa.Column("scope", ARTICLE_LABEL_SCOPE, nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "entities",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "locations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "labeled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "severity IS NULL OR (severity >= 1 AND severity <= 5)",
            name="ck_article_labels_severity_range",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_article_labels_confidence_range",
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "article_id",
            "prompt_version",
            name="uq_article_labels_article_prompt",
        ),
    )
    op.create_index(
        "idx_article_labels_is_event_labeled",
        "article_labels",
        ["is_event", "labeled_at"],
    )

    op.create_table(
        "article_embeddings",
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("embedding", HALFVEC(2048), nullable=False),
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
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id"),
    )
    op.create_index(
        "idx_article_embeddings_embedding",
        "article_embeddings",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "halfvec_cosine_ops"},
    )
    op.create_index(
        "idx_article_embeddings_created_at",
        "article_embeddings",
        ["created_at"],
    )


def downgrade() -> None:
    """Remove the article ledger, labels, and embeddings."""
    op.drop_index(
        "idx_article_embeddings_created_at",
        table_name="article_embeddings",
    )
    op.drop_index(
        "idx_article_embeddings_embedding",
        table_name="article_embeddings",
    )
    op.drop_table("article_embeddings")

    op.drop_index(
        "idx_article_labels_is_event_labeled",
        table_name="article_labels",
    )
    op.drop_table("article_labels")

    op.drop_index(
        "idx_articles_ingest_status_published_at",
        table_name="articles",
    )
    op.drop_index("idx_articles_canonical_url", table_name="articles")
    op.drop_index("idx_articles_content_hash", table_name="articles")

    op.drop_column("articles", "ingest_status")
    op.drop_column("articles", "language")
    op.drop_column("articles", "title_simhash")
    op.drop_column("articles", "content_hash")
    op.drop_column("articles", "feed_content")
    op.drop_column("articles", "feed_summary")
    op.drop_column("articles", "canonical_url")

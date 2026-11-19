"""add article analysis, labels, and syndication families

Revision ID: a3b4c5d6e7f8
Revises: f6a7b8c9d0e1
Create Date: 2026-11-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import HALFVEC


# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ARTICLE_BODY_SOURCE = sa.Enum(
    "FULL_TEXT",
    "FEED_SUMMARY",
    name="articlebodysource",
    native_enum=False,
)
ARTICLE_REJECT_STAGE = sa.Enum(
    "LABEL",
    "GATE",
    name="articlerejectstage",
    native_enum=False,
)
ARTICLE_CATEGORY = sa.Enum(
    "CONFLICT",
    "DISASTER",
    "ECONOMY",
    "POLITICS",
    "TECHNOLOGY",
    "SCIENCE",
    "HEALTH",
    "ENVIRONMENT",
    "SPORTS",
    "ENTERTAINMENT",
    "OTHER",
    name="articlecategory",
    native_enum=False,
)
ARTICLE_EVENT_FORM = sa.Enum(
    "INCIDENT",
    "PLANNED_EVENT",
    "POLICY_ACTION",
    "STATEMENT",
    "REPORT",
    "MARKET_MOVE",
    "OTHER",
    name="articleeventform",
    native_enum=False,
)
ARTICLE_CERTAINTY = sa.Enum(
    "CONFIRMED",
    "REPORTED",
    "ALLEGED",
    "DISPUTED",
    name="articlecertainty",
    native_enum=False,
)


def upgrade() -> None:
    """Add transient-fetch, label, embedding, and family fields."""
    op.create_table(
        "article_families",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("representative_article_id", sa.Uuid(), nullable=True),
        sa.Column("title_simhash", sa.String(length=16), nullable=False),
        sa.Column("body_simhash", sa.String(length=16), nullable=True),
        sa.Column("primary_origin_group", sa.String(length=64), nullable=False),
        sa.Column(
            "member_count",
            sa.Integer(),
            server_default="1",
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
            "member_count >= 1",
            name="ck_article_families_member_count_positive",
        ),
        sa.ForeignKeyConstraint(
            ["representative_article_id"],
            ["articles.id"],
            name="fk_article_families_representative_article_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_article_families_representative",
        "article_families",
        ["representative_article_id"],
    )
    op.create_index(
        "idx_article_families_origin_group",
        "article_families",
        ["primary_origin_group"],
    )
    op.create_index(
        "idx_article_families_updated_at",
        "article_families",
        ["updated_at"],
    )

    op.add_column("articles", sa.Column("family_id", sa.Uuid(), nullable=True))
    op.add_column(
        "articles",
        sa.Column("body_simhash", sa.String(length=16), nullable=True),
    )
    op.add_column("articles", sa.Column("word_count", sa.Integer(), nullable=True))
    op.add_column(
        "articles",
        sa.Column("body_source", ARTICLE_BODY_SOURCE, nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("input_quality", sa.Float(), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("fetch_http_status", sa.Integer(), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("reject_stage", ARTICLE_REJECT_STAGE, nullable=True),
    )
    op.add_column("articles", sa.Column("reject_reason", sa.Text(), nullable=True))
    op.add_column(
        "articles",
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_articles_family_id",
        "articles",
        "article_families",
        ["family_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_articles_family_id", "articles", ["family_id"])
    op.create_check_constraint(
        "ck_articles_body_source",
        "articles",
        "body_source IS NULL OR body_source IN ('FULL_TEXT', 'FEED_SUMMARY')",
    )
    op.create_check_constraint(
        "ck_articles_reject_stage",
        "articles",
        "reject_stage IS NULL OR reject_stage IN ('LABEL', 'GATE')",
    )

    op.add_column(
        "article_labels",
        sa.Column("category", ARTICLE_CATEGORY, nullable=True),
    )
    op.add_column(
        "article_labels",
        sa.Column("event_form", ARTICLE_EVENT_FORM, nullable=True),
    )
    op.add_column(
        "article_labels",
        sa.Column("specificity", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "article_labels",
        sa.Column("consequence", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "article_labels",
        sa.Column("certainty", ARTICLE_CERTAINTY, nullable=True),
    )
    op.add_column(
        "article_labels",
        sa.Column("reject_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "article_labels",
        sa.Column("input_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "article_labels",
        sa.Column("evidence_quote", sa.String(length=400), nullable=True),
    )
    op.create_check_constraint(
        "ck_article_labels_article_type",
        "article_labels",
        "article_type IN "
        "('BREAKING', 'DEVELOPMENT', 'ANALYSIS', 'FEATURE', 'OPINION', "
        "'LISTICLE', 'OTHER')",
    )
    op.create_check_constraint(
        "ck_article_labels_category",
        "article_labels",
        "category IS NULL OR category IN "
        "('CONFLICT', 'DISASTER', 'ECONOMY', 'POLITICS', 'TECHNOLOGY', "
        "'SCIENCE', 'HEALTH', 'ENVIRONMENT', 'SPORTS', 'ENTERTAINMENT', "
        "'OTHER')",
    )
    op.create_check_constraint(
        "ck_article_labels_event_form",
        "article_labels",
        "event_form IS NULL OR event_form IN "
        "('INCIDENT', 'PLANNED_EVENT', 'POLICY_ACTION', 'STATEMENT', "
        "'REPORT', 'MARKET_MOVE', 'OTHER')",
    )
    op.create_check_constraint(
        "ck_article_labels_certainty",
        "article_labels",
        "certainty IS NULL OR certainty IN "
        "('CONFIRMED', 'REPORTED', 'ALLEGED', 'DISPUTED')",
    )
    op.create_check_constraint(
        "ck_article_labels_specificity_range",
        "article_labels",
        "specificity IS NULL OR (specificity >= 1 AND specificity <= 5)",
    )
    op.create_check_constraint(
        "ck_article_labels_consequence_range",
        "article_labels",
        "consequence IS NULL OR (consequence >= 1 AND consequence <= 5)",
    )
    op.create_index(
        "idx_article_labels_entities_gin",
        "article_labels",
        ["entities"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_article_labels_locations_gin",
        "article_labels",
        ["locations"],
        postgresql_using="gin",
    )

    op.add_column(
        "articles",
        sa.Column("embedding", HALFVEC(2048), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("embedding_input_hash", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "ck_articles_embedding_metadata",
        "articles",
        "(embedding IS NULL AND embedding_model IS NULL "
        "AND embedding_input_hash IS NULL) "
        "OR (embedding IS NOT NULL AND embedding_model IS NOT NULL "
        "AND embedding_input_hash IS NOT NULL)",
    )
    op.create_index(
        "idx_articles_embedding",
        "articles",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "halfvec_cosine_ops"},
    )
    # Phase 2 created the sidecar but never wrote to it; Phase 3 owns the first
    # embedding write, so there is no data to migrate.
    op.drop_table("article_embeddings")


def downgrade() -> None:
    """Remove article analysis, label, embedding, and family fields."""
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
    op.execute(
        "INSERT INTO article_embeddings (article_id, model, embedding) "
        "SELECT id, embedding_model, embedding FROM articles "
        "WHERE embedding IS NOT NULL"
    )
    op.drop_constraint("ck_articles_embedding_metadata", "articles", type_="check")
    op.drop_index("idx_articles_embedding", table_name="articles")
    op.drop_column("articles", "embedding_input_hash")
    op.drop_column("articles", "embedding_model")
    op.drop_column("articles", "embedding")

    op.drop_index("idx_article_labels_locations_gin", table_name="article_labels")
    op.drop_index("idx_article_labels_entities_gin", table_name="article_labels")
    op.drop_constraint(
        "ck_article_labels_consequence_range",
        "article_labels",
        type_="check",
    )
    op.drop_constraint(
        "ck_article_labels_specificity_range",
        "article_labels",
        type_="check",
    )
    op.drop_constraint(
        "ck_article_labels_certainty",
        "article_labels",
        type_="check",
    )
    op.drop_constraint(
        "ck_article_labels_event_form",
        "article_labels",
        type_="check",
    )
    op.drop_constraint(
        "ck_article_labels_category",
        "article_labels",
        type_="check",
    )
    op.drop_constraint(
        "ck_article_labels_article_type",
        "article_labels",
        type_="check",
    )
    for column in (
        "evidence_quote",
        "input_hash",
        "reject_reason",
        "certainty",
        "consequence",
        "specificity",
        "event_form",
        "category",
    ):
        op.drop_column("article_labels", column)

    op.drop_constraint("ck_articles_reject_stage", "articles", type_="check")
    op.drop_constraint("ck_articles_body_source", "articles", type_="check")
    op.drop_index("idx_articles_family_id", table_name="articles")
    op.drop_constraint("fk_articles_family_id", "articles", type_="foreignkey")
    for column in (
        "rejected_at",
        "reject_reason",
        "reject_stage",
        "fetch_http_status",
        "input_quality",
        "body_source",
        "word_count",
        "body_simhash",
        "family_id",
    ):
        op.drop_column("articles", column)

    op.drop_index("idx_article_families_updated_at", table_name="article_families")
    op.drop_index("idx_article_families_origin_group", table_name="article_families")
    op.drop_index(
        "idx_article_families_representative",
        table_name="article_families",
    )
    op.drop_table("article_families")

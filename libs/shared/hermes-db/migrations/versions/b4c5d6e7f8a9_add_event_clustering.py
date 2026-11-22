"""add event clustering, membership, and verification

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-11-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b4c5d6e7f8a9"
down_revision: str | Sequence[str] | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ASSIGNMENT_METHOD = sa.Enum(
    "AUTO",
    "LLM",
    "MANUAL",
    name="assignmentmethod",
    native_enum=False,
)
CLUSTER_DECISION = sa.Enum(
    "SAME",
    "DIFFERENT",
    "UNSURE",
    name="clusterdecisionkind",
    native_enum=False,
)


def upgrade() -> None:
    """Add current/historical event membership and cached adjudications."""
    op.create_table(
        "event_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "method",
            ASSIGNMENT_METHOD,
            server_default="AUTO",
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "score_breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("true"),
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
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_event_members_confidence_range",
        ),
        sa.CheckConstraint(
            "NOT is_current OR removed_at IS NULL",
            name="ck_event_members_current_removed_at",
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            name="fk_event_members_article_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name="fk_event_members_event_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_event_members_current_article",
        "event_members",
        ["article_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "idx_event_members_current_event",
        "event_members",
        ["event_id"],
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "idx_event_members_article_history",
        "event_members",
        ["article_id", "assigned_at"],
    )

    op.create_table(
        "cluster_decisions",
        sa.Column("pair_hash", sa.String(length=64), nullable=False),
        sa.Column("decision", CLUSTER_DECISION, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_cluster_decisions_confidence_range",
        ),
        sa.PrimaryKeyConstraint("pair_hash"),
    )

    op.add_column(
        "events",
        sa.Column("source_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "events",
        sa.Column("family_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "events",
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("last_member_added_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
    )

    op.add_column(
        "articles",
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("assignment_method", ASSIGNMENT_METHOD, nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("assignment_confidence", sa.Float(), nullable=True),
    )

    op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS verificationstatus")
    op.create_check_constraint(
        "ck_events_verification_status",
        "events",
        "verification_status IN "
        "('CONFIRMED', 'CORROBORATED', 'SINGLE_SOURCE', "
        "'CONFLICTING', 'UNVERIFIED')",
    )
    op.create_check_constraint(
        "ck_events_importance_range",
        "events",
        "importance_score >= 0.0 AND importance_score <= 100.0",
    )
    op.create_check_constraint(
        "ck_events_counts_nonnegative",
        "events",
        "article_count >= 0 AND source_count >= 0 AND family_count >= 0 "
        "AND independent_origin_count >= 0",
    )
    op.create_check_constraint(
        "ck_articles_assignment_method",
        "articles",
        "assignment_method IS NULL OR assignment_method IN "
        "('AUTO', 'LLM', 'MANUAL')",
    )
    op.create_check_constraint(
        "ck_articles_assignment_confidence",
        "articles",
        "assignment_confidence IS NULL "
        "OR (assignment_confidence >= 0.0 AND assignment_confidence <= 1.0)",
    )

    # The phase 5 score replaces the legacy trending index immediately; keeping
    # both would leave the old score as the only active-event ordering index.
    op.drop_index("idx_events_active_score", table_name="events")
    op.create_index(
        "idx_events_active_importance",
        "events",
        [sa.text("importance_score DESC")],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.drop_index("idx_events_active_selection", table_name="events")
    op.create_index(
        "idx_events_active_selection",
        "events",
        ["selection_tier", sa.text("importance_score DESC")],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    """Remove membership, adjudication, and clustering provenance."""
    op.drop_index("idx_events_active_selection", table_name="events")
    op.create_index(
        "idx_events_active_selection",
        "events",
        ["selection_tier", "importance_score"],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.drop_index("idx_events_active_importance", table_name="events")
    op.create_index(
        "idx_events_active_score",
        "events",
        ["trending_score"],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.drop_constraint("ck_articles_assignment_confidence", "articles", type_="check")
    op.drop_constraint("ck_articles_assignment_method", "articles", type_="check")
    op.drop_constraint("ck_events_counts_nonnegative", "events", type_="check")
    op.drop_constraint("ck_events_importance_range", "events", type_="check")
    op.drop_constraint("ck_events_verification_status", "events", type_="check")

    op.drop_column("articles", "assignment_confidence")
    op.drop_column("articles", "assignment_method")
    op.drop_column("articles", "assigned_at")

    op.drop_column("events", "embedding_model")
    op.drop_column("events", "last_member_added_at")
    op.drop_column("events", "first_seen_at")
    op.drop_column("events", "family_count")
    op.drop_column("events", "source_count")

    op.drop_table("cluster_decisions")
    op.drop_index("idx_event_members_article_history", table_name="event_members")
    op.drop_index("idx_event_members_current_event", table_name="event_members")
    op.drop_index("uq_event_members_current_article", table_name="event_members")
    op.drop_table("event_members")

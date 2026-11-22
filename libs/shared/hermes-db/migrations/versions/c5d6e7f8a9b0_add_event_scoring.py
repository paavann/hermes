"""add event scoring, selection, and timeline provenance

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-11-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c5d6e7f8a9b0"
down_revision: str | Sequence[str] | None = "b4c5d6e7f8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store the explainable importance score and description provenance."""
    op.add_column(
        "events",
        sa.Column(
            "score_breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column("score_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("selection_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column(
            "locations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )

    # New events start as filler until the score stage runs. Existing rows keep
    # whatever their last run decided.
    op.alter_column(
        "events",
        "selection_tier",
        existing_type=sa.String(length=9),
        server_default="FILLER",
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_events_selection_tier",
        "events",
        "selection_tier IN ('PRIMARY', 'FILLER', 'DROP')",
    )

    op.add_column(
        "event_timelines",
        sa.Column("event_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "event_timelines",
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "event_timelines",
        sa.Column("model", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    """Remove scoring, selection, and timeline provenance fields."""
    op.drop_column("event_timelines", "model")
    op.drop_column("event_timelines", "prompt_version")
    op.drop_column("event_timelines", "event_version")

    op.drop_constraint("ck_events_selection_tier", "events", type_="check")
    op.alter_column(
        "events",
        "selection_tier",
        existing_type=sa.String(length=9),
        server_default="DROP",
        existing_nullable=False,
    )
    op.drop_column("events", "locations")
    op.drop_column("events", "selected_at")
    op.drop_column("events", "selection_reason")
    op.drop_column("events", "scored_at")
    op.drop_column("events", "score_version")
    op.drop_column("events", "score_breakdown")

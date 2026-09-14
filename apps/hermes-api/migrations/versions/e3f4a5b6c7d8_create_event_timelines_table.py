"""create event_timelines table

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-09-14 15:08:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_timelines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("nodes", JSONB(), nullable=False, server_default="[]"),
        sa.Column("edges", JSONB(), nullable=False, server_default="[]"),
        sa.Column("topic_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("gdelt_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_analyzed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "needs_refresh",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_event_timelines_event_id"),
    )
    op.create_index(
        "ix_event_timelines_event_id",
        "event_timelines",
        ["event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_event_timelines_event_id", table_name="event_timelines")
    op.drop_table("event_timelines")

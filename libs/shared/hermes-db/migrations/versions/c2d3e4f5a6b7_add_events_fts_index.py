"""add events full-text search index

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-11-07 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CREATE_FTS_INDEX = """
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_fts
ON events
USING gin (
    (
        setweight(to_tsvector('english'::regconfig, coalesce(ai_headline, '')), 'A') ||
        setweight(to_tsvector('english'::regconfig, coalesce(ai_summary, '')), 'B') ||
        setweight(to_tsvector('english'::regconfig, coalesce(location_name, '')), 'B') ||
        setweight(to_tsvector('english'::regconfig, coalesce(category, '')), 'C')
    )
)
"""

DROP_FTS_INDEX = "DROP INDEX CONCURRENTLY IF EXISTS idx_events_fts"


def upgrade() -> None:
    # CONCURRENTLY cannot run inside a transaction, so use an autocommit block.
    with op.get_context().autocommit_block():
        op.execute(CREATE_FTS_INDEX)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(DROP_FTS_INDEX)

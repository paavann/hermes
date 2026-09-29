"""purge null geocode cache

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-09-23 16:30:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Purge any geocode cache entries saved with NULL coordinates during 429 rate limit floods
    op.execute("DELETE FROM geocode_cache WHERE latitude IS NULL;")


def downgrade() -> None:
    pass

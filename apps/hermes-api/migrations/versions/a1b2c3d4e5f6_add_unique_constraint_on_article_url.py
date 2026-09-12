"""add unique constraint on article url.

Revision ID: a1b2c3d4e5f6
Revises: b8446b410d52
Create Date: 2026-09-12 15:24:00.000000

"""
from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b8446b410d52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_articles_url",
        "articles",
        ["url"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_articles_url", "articles", type_="unique")

"""add impact level and velocity to events

Revision ID: b1c2d3e4f5a6
Revises: f5a6b7c8d9e0
Create Date: 2026-10-19 00:37:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update sourcetype enum to add GDELT
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'GDELT';")

    # 2. Create impactlevel enum
    impact_level_enum = sa.Enum("CRITICAL", "MAJOR", "MODERATE", "MINOR", name="impactlevel")
    impact_level_enum.create(op.get_bind(), checkfirst=True)

    # 3. Add columns to events table
    op.add_column(
        "events",
        sa.Column(
            "impact_level",
            sa.Enum("CRITICAL", "MAJOR", "MODERATE", "MINOR", name="impactlevel"),
            nullable=False,
            server_default="MODERATE",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "velocity",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "velocity")
    op.drop_column("events", "impact_level")
    op.execute("DROP TYPE IF EXISTS impactlevel;")

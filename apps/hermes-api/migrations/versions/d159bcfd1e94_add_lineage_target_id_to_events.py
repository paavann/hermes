"""add lineage_target_id to events

Revision ID: d159bcfd1e94
Revises: e3f4a5b6c7d8
Create Date: 2026-09-14 17:10:11.772195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd159bcfd1e94'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('events', sa.Column('lineage_target_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_events_lineage_target_id', 'events', 'events', 
        ['lineage_target_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_events_lineage_target_id', 'events', type_='foreignkey')
    op.drop_column('events', 'lineage_target_id')

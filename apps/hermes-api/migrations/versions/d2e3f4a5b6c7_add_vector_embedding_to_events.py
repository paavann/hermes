"""add vector embedding to events

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-09-12 16:36:00.000000

"""
from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ensure the vector extension exists
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    
    # 2. Add the column
    op.add_column('events', sa.Column('embedding', Vector(dim=768), nullable=True))
    
    # 3. Add the HNSW index
    op.create_index(
        'idx_events_embedding',
        'events',
        ['embedding'],
        unique=False,
        postgresql_using='hnsw',
        postgresql_with={'m': 16, 'ef_construction': 64},
        postgresql_ops={'embedding': 'vector_cosine_ops'}
    )


def downgrade() -> None:
    op.drop_index('idx_events_embedding', table_name='events')
    op.drop_column('events', 'embedding')
    # Intentionally not dropping the extension as other tables might use it

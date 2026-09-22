"""update embedding to halfvec 2048

Revision ID: e4f5a6b7c8d9
Revises: 67c2d30edccd
Create Date: 2026-09-23 00:58:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "67c2d30edccd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop existing HNSW index
    op.drop_index("idx_events_embedding", table_name="events")

    # 2. Reset existing 768-dim embeddings since they cannot be cast directly to 2048-dim
    op.execute("UPDATE events SET embedding = NULL WHERE embedding IS NOT NULL;")

    # 3. Alter column type to halfvec(2048)
    op.execute("ALTER TABLE events ALTER COLUMN embedding TYPE halfvec(2048);")

    # 4. Recreate HNSW index for halfvec(2048) with halfvec_cosine_ops
    op.create_index(
        "idx_events_embedding",
        "events",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "halfvec_cosine_ops"},
    )


def downgrade() -> None:
    # 1. Drop HNSW halfvec index
    op.drop_index("idx_events_embedding", table_name="events")

    # 2. Reset embeddings before converting back to 768-dim
    op.execute("UPDATE events SET embedding = NULL WHERE embedding IS NOT NULL;")

    # 3. Alter column type back to vector(768)
    op.execute("ALTER TABLE events ALTER COLUMN embedding TYPE vector(768);")

    # 4. Recreate HNSW index with vector_cosine_ops
    op.create_index(
        "idx_events_embedding",
        "events",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

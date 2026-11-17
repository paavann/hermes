from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin


if TYPE_CHECKING:
    from hermes_db.models.article import Article


class ArticleEmbedding(Base, TimestampMixin):
    __tablename__ = "article_embeddings"

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model: Mapped[str] = mapped_column(String(128))
    embedding: Mapped[list[float]] = mapped_column(HALFVEC(2048))

    article: Mapped[Article] = relationship(
        back_populates="embedding_record",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "idx_article_embeddings_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "halfvec_cosine_ops"},
        ),
        Index("idx_article_embeddings_created_at", "created_at"),
    )

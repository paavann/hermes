from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import IngestStatus


if TYPE_CHECKING:
    from hermes_db.models.article_embedding import ArticleEmbedding
    from hermes_db.models.article_label import ArticleLabel
    from hermes_db.models.event import Event
    from hermes_db.models.source import Source


class Article(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "articles"

    # Nullable so deleting an event cannot delete its ledger articles.
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, unique=True)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)

    feed_summary: Mapped[str | None] = mapped_column(Text)
    feed_content: Mapped[str | None] = mapped_column(Text)

    published_at: Mapped[datetime | None] = mapped_column()
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())

    content_hash: Mapped[str | None] = mapped_column(String(64))
    # 64-bit SimHash as a 16-character hex digest.
    title_simhash: Mapped[str | None] = mapped_column(String(16))
    language: Mapped[str | None] = mapped_column(String(16))
    ingest_status: Mapped[IngestStatus] = mapped_column(
        Enum(
            IngestStatus,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=IngestStatus.NEW,
        server_default=IngestStatus.NEW.value,
    )

    # article claim queue fields.
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[str | None] = mapped_column(String(128))
    attempt_count: Mapped[int] = mapped_column(default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)

    event: Mapped[Event | None] = relationship(back_populates="articles")
    source: Mapped[Source | None] = relationship(
        back_populates="articles", lazy="selectin"
    )
    labels: Mapped[list[ArticleLabel]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    embedding_record: Mapped[ArticleEmbedding | None] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
        uselist=False,
    )

    __table_args__ = (
        Index("idx_articles_content_hash", "content_hash"),
        Index("idx_articles_canonical_url", "canonical_url"),
        Index(
            "idx_articles_ingest_status_published_at",
            "ingest_status",
            "published_at",
        ),
        Index("idx_articles_event_id", "event_id"),
        Index("idx_articles_source_id", "source_id"),
        Index(
            "idx_articles_analyzing_claimed_at",
            "claimed_at",
            postgresql_where=text("ingest_status = 'ANALYZING'"),
        ),
    )

    @property
    def source_name(self) -> str | None:
        return self.source.name if self.source else None

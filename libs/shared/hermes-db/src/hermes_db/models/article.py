from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text, func
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

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE")
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

    event: Mapped[Event] = relationship(back_populates="articles")
    source: Mapped[Source] = relationship(back_populates="articles", lazy="selectin")
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
    )

    @property
    def source_name(self) -> str | None:
        return self.source.name if self.source else None

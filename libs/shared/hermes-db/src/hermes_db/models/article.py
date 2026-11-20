from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import (
    ArticleBodySource,
    AssignmentMethod,
    IngestStatus,
    RejectStage,
)


if TYPE_CHECKING:
    from hermes_db.models.article_label import ArticleLabel
    from hermes_db.models.event import Event
    from hermes_db.models.event_member import EventMember
    from hermes_db.models.source import Source


class Article(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "articles"

    # nullable so deleting an event cannot delete its ledger articles.
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
    # sha256 of canonical_url. partial unique index where the article is not a
    # known duplicate keeps URL variants from creating separate ledger rows.
    canonical_url_hash: Mapped[str | None] = mapped_column(String(64))
    thumbnail_url: Mapped[str | None] = mapped_column(Text)

    # set only when a backfill or reconciliation resolved this row as a copy of
    # an article already in the ledger. ingest skips such rows instead.
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
    )

    feed_summary: Mapped[str | None] = mapped_column(Text)

    published_at: Mapped[datetime | None] = mapped_column()
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())

    content_hash: Mapped[str | None] = mapped_column(String(64))
    # 64-bit simhash as a 16-character hex digest.
    title_simhash: Mapped[str | None] = mapped_column(String(16))
    body_simhash: Mapped[str | None] = mapped_column(String(16))
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_source: Mapped[ArticleBodySource | None] = mapped_column(
        Enum(
            ArticleBodySource,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="articlebodysource",
        ),
        nullable=True,
    )
    input_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetch_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # stored on the ledger so family matching does not need a second table.
    # deferred keeps the 4 KB vector out of ordinary article selects.
    embedding: Mapped[list[float] | None] = mapped_column(
        HALFVEC(2048),
        nullable=True,
        deferred=True,
    )
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_input_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    family_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("article_families.id", ondelete="SET NULL"),
        nullable=True,
    )
    reject_stage: Mapped[RejectStage | None] = mapped_column(
        Enum(
            RejectStage,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="articlerejectstage",
        ),
        nullable=True,
    )
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
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

    # current event assignment provenance; history lives in event_members.
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignment_method: Mapped[AssignmentMethod | None] = mapped_column(
        Enum(
            AssignmentMethod,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="assignmentmethod",
        ),
        nullable=True,
    )
    assignment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

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
    memberships: Mapped[list[EventMember]] = relationship(
        back_populates="article",
        passive_deletes=True,
        lazy="raise",
    )

    __table_args__ = (
        CheckConstraint(
            "body_source IS NULL OR body_source IN ('FULL_TEXT', 'FEED_SUMMARY')",
            name="ck_articles_body_source",
        ),
        CheckConstraint(
            "reject_stage IS NULL OR reject_stage IN ('LABEL', 'GATE')",
            name="ck_articles_reject_stage",
        ),
        CheckConstraint(
            "(embedding IS NULL AND embedding_model IS NULL "
            "AND embedding_input_hash IS NULL) "
            "OR (embedding IS NOT NULL AND embedding_model IS NOT NULL "
            "AND embedding_input_hash IS NOT NULL)",
            name="ck_articles_embedding_metadata",
        ),
        CheckConstraint(
            "assignment_method IS NULL OR assignment_method IN "
            "('AUTO', 'LLM', 'MANUAL')",
            name="ck_articles_assignment_method",
        ),
        CheckConstraint(
            "assignment_confidence IS NULL "
            "OR (assignment_confidence >= 0.0 AND assignment_confidence <= 1.0)",
            name="ck_articles_assignment_confidence",
        ),
        Index(
            "idx_articles_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "halfvec_cosine_ops"},
        ),
        Index("idx_articles_content_hash", "content_hash"),
        Index("idx_articles_canonical_url", "canonical_url"),
        Index(
            "idx_articles_ingest_status_published_at",
            "ingest_status",
            "published_at",
        ),
        Index("idx_articles_event_id", "event_id"),
        Index("idx_articles_source_id", "source_id"),
        Index("idx_articles_family_id", "family_id"),
        Index(
            "idx_articles_analyzing_claimed_at",
            "claimed_at",
            postgresql_where=text("ingest_status = 'ANALYZING'"),
        ),
        Index(
            "uq_articles_canonical_url_hash",
            "canonical_url_hash",
            unique=True,
            postgresql_where=text(
                "canonical_url_hash IS NOT NULL AND duplicate_of_id IS NULL"
            ),
        ),
        Index("idx_articles_duplicate_of_id", "duplicate_of_id"),
    )

    @property
    def source_name(self) -> str | None:
        return self.source.name if self.source else None

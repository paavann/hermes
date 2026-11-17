from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import ArticleType, EventScope


if TYPE_CHECKING:
    from hermes_db.models.article import Article


class ArticleLabel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "article_labels"

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE")
    )
    prompt_version: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))

    is_event: Mapped[bool] = mapped_column(Boolean)
    article_type: Mapped[ArticleType] = mapped_column(
        Enum(
            ArticleType,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=ArticleType.OTHER,
        server_default=ArticleType.OTHER.value,
    )
    event_time: Mapped[datetime | None] = mapped_column(nullable=True)
    severity: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    scope: Mapped[EventScope | None] = mapped_column(
        Enum(
            EventScope,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="articlelabelscope",
        ),
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    entities: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )
    locations: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )

    labeled_at: Mapped[datetime] = mapped_column(server_default=func.now())

    article: Mapped[Article] = relationship(back_populates="labels", lazy="raise")

    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "prompt_version",
            name="uq_article_labels_article_prompt",
        ),
        CheckConstraint(
            "severity IS NULL OR (severity >= 1 AND severity <= 5)",
            name="ck_article_labels_severity_range",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_article_labels_confidence_range",
        ),
        Index("idx_article_labels_is_event_labeled", "is_event", "labeled_at"),
    )

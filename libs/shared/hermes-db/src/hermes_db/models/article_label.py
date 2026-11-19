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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import (
    ArticleCategory,
    ArticleCertainty,
    ArticleType,
    EventForm,
    EventScope,
)


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

    fact: Mapped[str | None] = mapped_column(Text, nullable=True)
    scale_facts: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    category: Mapped[ArticleCategory | None] = mapped_column(
        Enum(
            ArticleCategory,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="articlecategory",
        ),
        nullable=True,
    )
    event_form: Mapped[EventForm | None] = mapped_column(
        Enum(
            EventForm,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="articleeventform",
        ),
        nullable=True,
    )
    specificity: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    consequence: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    certainty: Mapped[ArticleCertainty | None] = mapped_column(
        Enum(
            ArticleCertainty,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="articlecertainty",
        ),
        nullable=True,
    )
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_quote: Mapped[str | None] = mapped_column(String(400), nullable=True)

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
        CheckConstraint(
            "article_type IN "
            "('BREAKING', 'DEVELOPMENT', 'ANALYSIS', 'FEATURE', 'OPINION', "
            "'LISTICLE', 'OTHER')",
            name="ck_article_labels_article_type",
        ),
        CheckConstraint(
            "category IS NULL OR category IN "
            "('CONFLICT', 'DISASTER', 'ECONOMY', 'POLITICS', 'TECHNOLOGY', "
            "'SCIENCE', 'HEALTH', 'ENVIRONMENT', 'SPORTS', 'ENTERTAINMENT', "
            "'OTHER')",
            name="ck_article_labels_category",
        ),
        CheckConstraint(
            "event_form IS NULL OR event_form IN "
            "('INCIDENT', 'PLANNED_EVENT', 'POLICY_ACTION', 'STATEMENT', "
            "'REPORT', 'MARKET_MOVE', 'OTHER')",
            name="ck_article_labels_event_form",
        ),
        CheckConstraint(
            "certainty IS NULL OR certainty IN "
            "('CONFIRMED', 'REPORTED', 'ALLEGED', 'DISPUTED')",
            name="ck_article_labels_certainty",
        ),
        CheckConstraint(
            "specificity IS NULL OR (specificity >= 1 AND specificity <= 5)",
            name="ck_article_labels_specificity_range",
        ),
        CheckConstraint(
            "consequence IS NULL OR (consequence >= 1 AND consequence <= 5)",
            name="ck_article_labels_consequence_range",
        ),
        Index("idx_article_labels_is_event_labeled", "is_event", "labeled_at"),
        Index(
            "idx_article_labels_entities_gin",
            "entities",
            postgresql_using="gin",
        ),
        Index(
            "idx_article_labels_locations_gin",
            "locations",
            postgresql_using="gin",
        ),
    )

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import (
    CredibilityTier,
    SourceFeedProvider,
    SourceFetchPolicy,
    SourceType,
)


if TYPE_CHECKING:
    from hermes_db.models.article import Article


class Source(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(128), unique=True)

    url: Mapped[str] = mapped_column(Text)
    feed_url: Mapped[str | None] = mapped_column(Text)
    # second feed tried only when the primary returns no entries or errors.
    fallback_feed_url: Mapped[str | None] = mapped_column(Text)
    feed_provider: Mapped[SourceFeedProvider] = mapped_column(
        Enum(
            SourceFeedProvider,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=SourceFeedProvider.PUBLISHER,
        server_default=SourceFeedProvider.PUBLISHER.value,
    )
    canonical_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paywall: Mapped[bool] = mapped_column(default=False, server_default="false")
    fetch_policy: Mapped[SourceFetchPolicy] = mapped_column(
        Enum(
            SourceFetchPolicy,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=SourceFetchPolicy.FULL_TEXT,
        server_default=SourceFetchPolicy.FULL_TEXT.value,
    )

    source_type: Mapped[SourceType] = mapped_column(default=SourceType.RSS)
    credibility: Mapped[CredibilityTier] = mapped_column(default=CredibilityTier.TIER_3)

    # Wire/origin family used to avoid counting republished copies as independent.
    origin_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)
    logo_url: Mapped[str | None] = mapped_column(Text)
    # Last fetch attempt (success or failure); failures also advance this timestamp
    # so retry backoff has a stable anchor.
    last_fetched_at: Mapped[datetime | None] = mapped_column()
    fetch_interval_minutes: Mapped[int] = mapped_column(default=15)

    # Fetch health. Backoff derives from last_fetched_at + consecutive_failures.
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    articles: Mapped[list[Article]] = relationship(
        back_populates="source",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "idx_sources_origin_group",
            "origin_group",
            postgresql_where=text("origin_group IS NOT NULL"),
        ),
        Index("idx_sources_canonical_domain", "canonical_domain"),
    )

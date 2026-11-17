from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import CredibilityTier, SourceType


if TYPE_CHECKING:
    from hermes_db.models.article import Article


class Source(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(128), unique=True)

    url: Mapped[str] = mapped_column(Text)
    feed_url: Mapped[str | None] = mapped_column(Text)

    source_type: Mapped[SourceType] = mapped_column(default=SourceType.RSS)
    credibility: Mapped[CredibilityTier] = mapped_column(default=CredibilityTier.TIER_3)

    # Wire/origin family used to avoid counting republished copies as independent.
    origin_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)
    logo_url: Mapped[str | None] = mapped_column(Text)
    last_fetched_at: Mapped[datetime | None] = mapped_column()
    fetch_interval_minutes: Mapped[int] = mapped_column(default=15)

    # Fetch health. Backoff is derived from last_fetched_at + consecutive_failures.
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
    )

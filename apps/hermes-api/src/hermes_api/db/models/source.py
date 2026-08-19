from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import String, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_api.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from hermes_api.db.enums import SourceType, CredibilityTier

if TYPE_CHECKING:
    from hermes_api.db.models.article import Article




class Source(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    
    url: Mapped[str] = mapped_column(Text)
    feed_url: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[SourceType] = mapped_column(default=SourceType.RSS)

    credibility: Mapped[CredibilityTier] = mapped_column(default=CredibilityTier.TIER_3)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column()
    fetch_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)

    articles: Mapped[list["Article"]] = relationship(back_populates="source")    
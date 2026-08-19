from unicodedata import category
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, Text, Float, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from hermes_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_api.db.enums import EventStatus, EventScope


if TYPE_CHECKING:
    from hermes_api.db.models.article import Article




class Event(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "events"

    ai_headline: Mapped[str] = mapped_column(String(500))
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)

    category: Mapped[str] = mapped_column(String(100))
    category_color: Mapped[str] = mapped_column(String(7))
    status: Mapped[EventStatus] = mapped_column(default=EventStatus.ACTIVE)
    scope: Mapped[EventScope] = mapped_column(default=EventScope.COUNTRY)


    location: Mapped[str] = mapped_column(Geometry(
        geometry_type="POINT",
        srid=4326,
        spatial_index=False,
    ))
    location_name: Mapped[str] = mapped_column(String(255))
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    
    trending_score: Mapped[float] = mapped_column(Float, default=0.0)
    article_count: Mapped[int] = mapped_column(Integer, default=0)

    first_reported_at: Mapped[datetime] = mapped_column(server_default="now()",)
    last_updated_at: Mapped[datetime] = mapped_column(server_default="now()",)

    articles: Mapped[list["Article"]] = relationship(back_populates="event", cascade="all, delete-orphan")

    #indexes.
    __table_args__ = (
        Index("idx_events_location", "location", postgresql_using="gist"),
        Index("idx_events_active_score", "status", "trending_score", postgresql_where=(status==EventStatus.ACTIVE)),
        Index("idx_events_scope", "scope", "status"),
        Index("idx_events_country", "country_code", postgresql_where=(country_code.isnot(None))),
    )
    
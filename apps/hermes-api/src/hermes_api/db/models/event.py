from datetime import datetime
from typing import TYPE_CHECKING, Optional

from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_api.db.enums import EventScope, EventStatus

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


    location: Mapped[Optional[str]] = mapped_column(Geometry(
        geometry_type="POINT",
        srid=4326,
        spatial_index=False,
    ), nullable=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    
    trending_score: Mapped[float] = mapped_column(Float, default=0.0)
    article_count: Mapped[int] = mapped_column(Integer, default=0)

    first_reported_at: Mapped[datetime] = mapped_column(server_default="now()",)
    last_updated_at: Mapped[datetime] = mapped_column(server_default="now()",)

    articles: Mapped[list["Article"]] = relationship(back_populates="event", cascade="all, delete-orphan")

    # Semantic Embedding for fast deduplication
    embedding: Mapped[Optional["Vector"]] = mapped_column(Vector(768))

    #indexes.
    __table_args__ = (
        Index("idx_events_location", "location", postgresql_using="gist"),
        Index("idx_events_embedding", "embedding", postgresql_using="hnsw", postgresql_with={"m": 16, "ef_construction": 64}, postgresql_ops={"embedding": "vector_cosine_ops"}),
        Index("idx_events_active_score", "status", "trending_score", postgresql_where=text("status = 'ACTIVE'")),
        Index("idx_events_scope", "scope", "status"),
        Index("idx_events_country", "country_code", postgresql_where=text("country_code IS NOT NULL")),
    )
    
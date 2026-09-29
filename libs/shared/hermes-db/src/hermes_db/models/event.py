from pgvector.sqlalchemy import HALFVEC
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Float, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import EventScope, EventStatus

if TYPE_CHECKING:
    from hermes_db.models.article import Article

class Event(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "events"

    ai_headline: Mapped[str] = mapped_column(String(500))
    ai_summary: Mapped[str | None] = mapped_column(Text)

    category: Mapped[str] = mapped_column(String(100))
    category_color: Mapped[str] = mapped_column(String(7))

    status: Mapped[EventStatus] = mapped_column(default=EventStatus.ACTIVE)
    scope: Mapped[EventScope] = mapped_column(default=EventScope.COUNTRY)

    location: Mapped[str | None] = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            spatial_index=False,
        ),
        nullable=True,
    )
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)

    trending_score: Mapped[float] = mapped_column(Float, default=0.0)
    article_count: Mapped[int] = mapped_column(Integer, default=0)

    first_reported_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    articles: Mapped[list["Article"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    embedding: Mapped[HALFVEC | None] = mapped_column(HALFVEC(2048))

    __table_args__ = (
        Index("idx_events_location", "location", postgresql_using="gist"),
        Index(
            "idx_events_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={ "M": "16", "ef_construction": "64" },
            posgresql_ops={ "embedding": "halfvec_cosine_ops" },
        ),
        Index(
            "idx_events_active_score",
            "status",
            "trending_score",
            postgresql_where=text("status = 'ACTIVE'"),    
        ),
        Index("idx_events_scope", "scope", "status"),      
        Index(
            "idx_events_country",
            "country_code",
            postgresql_where=text("country_code IS NOT NULL"),
        ),
    )
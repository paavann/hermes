from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry, WKBElement
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import Float, Index, Integer, String, Text, func, literal_column, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import ColumnElement

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import EventScope, EventStatus, ImpactLevel


if TYPE_CHECKING:
    from hermes_db.models.article import Article


def event_fts_expression(
    headline: ColumnElement[str],
    summary: ColumnElement[str | None],
    location_name: ColumnElement[str | None],
    category: ColumnElement[str],
) -> ColumnElement[str]:
    regconfig = literal_column("'english'::regconfig")
    empty = literal_column("''")
    return (
        func.setweight(
            func.to_tsvector(regconfig, func.coalesce(headline, empty)),
            literal_column("'A'"),
        )
        .op("||")(
            func.setweight(
                func.to_tsvector(regconfig, func.coalesce(summary, empty)),
                literal_column("'B'"),
            )
        )
        .op("||")(
            func.setweight(
                func.to_tsvector(regconfig, func.coalesce(location_name, empty)),
                literal_column("'B'"),
            )
        )
        .op("||")(
            func.setweight(
                func.to_tsvector(regconfig, func.coalesce(category, empty)),
                literal_column("'C'"),
            )
        )
    )


class Event(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "events"

    ai_headline: Mapped[str] = mapped_column(String(500))
    ai_summary: Mapped[str | None] = mapped_column(Text)

    category: Mapped[str] = mapped_column(String(100))
    category_color: Mapped[str] = mapped_column(String(7))

    status: Mapped[EventStatus] = mapped_column(default=EventStatus.ACTIVE)
    scope: Mapped[EventScope] = mapped_column(default=EventScope.COUNTRY)
    impact_level: Mapped[ImpactLevel] = mapped_column(
        default=ImpactLevel.MODERATE,
        server_default=ImpactLevel.MODERATE.value,
    )

    location: Mapped[WKBElement | str | None] = mapped_column(
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
    velocity: Mapped[float] = mapped_column(Float, default=1.0, server_default="1.0")
    article_count: Mapped[int] = mapped_column(Integer, default=0)

    first_reported_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    articles: Mapped[list[Article]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    embedding: Mapped[list[float] | None] = mapped_column(HALFVEC(2048))

    __table_args__ = (
        Index("idx_events_location", "location", postgresql_using="gist"),
        Index(
            "idx_events_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "halfvec_cosine_ops"},
        ),
        Index(
            "idx_events_active_score",
            "trending_score",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("idx_events_scope", "scope", "status"),
        Index("idx_events_status_last_updated", "status", "last_updated_at"),
        Index(
            "idx_events_country",
            "country_code",
            postgresql_where=text("country_code IS NOT NULL"),
        ),
        Index(
            "idx_events_fts",
            event_fts_expression(
                literal_column("ai_headline"),
                literal_column("ai_summary"),
                literal_column("location_name"),
                literal_column("category"),
            ),
            postgresql_using="gin",
        ),
    )

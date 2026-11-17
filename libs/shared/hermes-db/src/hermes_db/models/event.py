import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry, WKBElement
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import (
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    literal_column,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import ColumnElement, SQLColumnExpression

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import (
    EventScope,
    EventStatus,
    ImpactLevel,
    SelectionTier,
    VerificationStatus,
)


if TYPE_CHECKING:
    from hermes_db.models.article import Article
    from hermes_db.models.thread import Thread


def event_fts_expression(
    headline: SQLColumnExpression[str],
    summary: SQLColumnExpression[str | None],
    location_name: SQLColumnExpression[str | None],
    category: SQLColumnExpression[str],
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

    event_time: Mapped[datetime | None] = mapped_column(nullable=True)
    latest_published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("threads.id", ondelete="SET NULL"),
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    importance_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0",
    )
    popularity_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0",
    )
    selection_tier: Mapped[SelectionTier] = mapped_column(
        Enum(
            SelectionTier,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=SelectionTier.DROP,
        server_default=SelectionTier.DROP.value,
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(
            VerificationStatus,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=VerificationStatus.UNVERIFIED,
        server_default=VerificationStatus.UNVERIFIED.value,
    )
    independent_origin_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    trending_score: Mapped[float] = mapped_column(Float, default=0.0)
    velocity: Mapped[float] = mapped_column(Float, default=1.0, server_default="1.0")
    article_count: Mapped[int] = mapped_column(Integer, default=0)

    # Synthesis cache key over the event's current member set.
    member_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Bumped only when a material field changes, so timelines can be invalidated.
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    first_reported_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # Ledger articles grouped under this event. The FK is SET NULL, so there is
    # deliberately no ORM delete cascade here.
    articles: Mapped[list[Article]] = relationship(
        back_populates="event",
        passive_deletes=True,
        lazy="raise",
    )
    thread: Mapped[Thread | None] = relationship(
        back_populates="events",
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
        Index(
            "idx_events_thread_id",
            "thread_id",
            postgresql_where=text("thread_id IS NOT NULL"),
        ),
        Index("idx_events_event_time", "event_time"),
        Index("idx_events_latest_published_at", "latest_published_at"),
        Index(
            "idx_events_active_selection",
            "selection_tier",
            "importance_score",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

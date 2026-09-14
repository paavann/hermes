import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from hermes_api.db.models.event import Event


class EventTimeline(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stores the AI-generated causal timeline graph for a given event.

    One record exists per event. It is updated in-place when the TTL expires
    or when needs_refresh is set by the ingestion pipeline. The nodes and
    edges columns store the accumulated geospatial storyline as JSONB so the
    schema can evolve without additional migrations.
    """

    __tablename__ = "event_timelines"

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # The accumulated graph data produced by Gemini.
    nodes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    edges: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    topic_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Metadata about the last generation run.
    gdelt_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Set to True by the ingestion pipeline when a new article is matched
    # to the parent event, signalling that the timeline should be refreshed
    # on the next "Analyze" click — regardless of TTL age.
    needs_refresh: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    event: Mapped["Event"] = relationship(back_populates="timeline")

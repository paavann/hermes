import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hermes_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_api.db.enums import EventTlStatus

class EventTl(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "event_timelines"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), unique=True, index=True)
    status: Mapped[EventTlStatus] = mapped_column(default=EventTlStatus.GENERATING, server_default="GENERATING")
    nodes: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    edges: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    tl_summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    wikipedia_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    node_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

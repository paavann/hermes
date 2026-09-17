from email.policy import default
from sqlalchemy.orm import mapped_column
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from hermes_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin




class EventTl(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "event_timelines"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="GENERATING", server_default="GENERATING")
    nodes: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    edges: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    tl_summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    wikipedia_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    node_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

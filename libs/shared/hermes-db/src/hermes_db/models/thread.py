from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import ThreadKind, ThreadStatus


if TYPE_CHECKING:
    from hermes_db.models.event import Event


class Thread(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "threads"

    kind: Mapped[ThreadKind] = mapped_column(
        Enum(
            ThreadKind,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=ThreadKind.DEVELOPING,
        server_default=ThreadKind.DEVELOPING.value,
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ThreadStatus] = mapped_column(
        Enum(
            ThreadStatus,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=ThreadStatus.ACTIVE,
        server_default=ThreadStatus.ACTIVE.value,
    )

    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    entities: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )
    keywords: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )

    importance: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    events: Mapped[list[Event]] = relationship(
        back_populates="thread",
        passive_deletes=True,
        lazy="raise",
    )

    __table_args__ = (
        Index("idx_threads_status_importance", "status", "importance"),
        Index("idx_threads_kind_status", "kind", "status"),
    )

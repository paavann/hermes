from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import Enum, Float, Index, Integer, String, Text
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
    # casefolded/whitespace-normalized name used for deterministic blocking.
    name_norm: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    event_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    last_event_at: Mapped[datetime | None] = mapped_column(nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        HALFVEC(2048),
        nullable=True,
        deferred=True,
    )
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    events: Mapped[list[Event]] = relationship(
        back_populates="thread",
        passive_deletes=True,
        lazy="raise",
    )

    __table_args__ = (
        Index("idx_threads_status_importance", "status", "importance"),
        Index("idx_threads_kind_status", "kind", "status"),
        Index("idx_threads_status_last_event", "status", "last_event_at"),
        Index("idx_threads_name_norm", "name_norm"),
        Index(
            "idx_threads_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "halfvec_cosine_ops"},
        ),
    )

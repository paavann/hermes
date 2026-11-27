from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    func,
    literal_column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import EventRelationshipType


if TYPE_CHECKING:
    from hermes_db.models.event import Event


class EventRelationship(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "event_relationships"

    source_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[EventRelationshipType] = mapped_column(
        Enum(
            EventRelationshipType,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="eventrelationshiptype",
        ),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(String(300), nullable=False)
    pair_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    source_event: Mapped[Event] = relationship(
        foreign_keys=[source_event_id],
        lazy="raise",
    )
    target_event: Mapped[Event] = relationship(
        foreign_keys=[target_event_id],
        lazy="raise",
    )

    __table_args__ = (
        CheckConstraint(
            "source_event_id <> target_event_id",
            name="ck_event_relationships_no_self_loop",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_event_relationships_confidence_range",
        ),
        Index(
            "uq_event_relationships_unordered_pair",
            func.least(
                literal_column("source_event_id"),
                literal_column("target_event_id"),
            ),
            func.greatest(
                literal_column("source_event_id"),
                literal_column("target_event_id"),
            ),
            unique=True,
        ),
        Index("idx_event_relationships_source", "source_event_id"),
        Index("idx_event_relationships_target", "target_event_id"),
    )

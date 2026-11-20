from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hermes_db.enums import AssignmentMethod


if TYPE_CHECKING:
    from hermes_db.models.article import Article
    from hermes_db.models.event import Event


class EventMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "event_members"

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE")
    )
    assigned_at: Mapped[datetime] = mapped_column(server_default=func.now())
    removed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    method: Mapped[AssignmentMethod] = mapped_column(
        Enum(
            AssignmentMethod,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="assignmentmethod",
        ),
        default=AssignmentMethod.AUTO,
        server_default=AssignmentMethod.AUTO.value,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    is_current: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
    )

    event: Mapped[Event] = relationship(back_populates="members")
    article: Mapped[Article] = relationship(back_populates="memberships")

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_event_members_confidence_range",
        ),
        CheckConstraint(
            "NOT is_current OR removed_at IS NULL",
            name="ck_event_members_current_removed_at",
        ),
        Index(
            "uq_event_members_current_article",
            "article_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
        Index(
            "idx_event_members_current_event",
            "event_id",
            postgresql_where=text("is_current"),
        ),
        Index("idx_event_members_article_history", "article_id", "assigned_at"),
    )

import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EventEdge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "event_edges"

    event_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    event_b_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    relationship_type: Mapped[str] = mapped_column(String(50), default="related")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Optional relationships to traverse the graph via ORM if needed
    # event_a = relationship("Event", foreign_keys=[event_a_id])
    # event_b = relationship("Event", foreign_keys=[event_b_id])

    __table_args__ = (
        UniqueConstraint("event_a_id", "event_b_id", "relationship_type", name="uq_event_edge"),
        CheckConstraint("event_a_id != event_b_id", name="check_no_self_edge"),
    )

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hermes_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StoryAllowlist(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Manual gating configuration for complex story timelines.

    Maps a dynamically generated Event (by its UUID) to one or more
    Wikipedia timeline pages. Only events present in this table will
    trigger the "Analyze" functionality in the UI.
    """

    __tablename__ = "story_allowlists"

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    wikipedia_page_title: Mapped[str] = mapped_column(String(255))

    # Optional ORM relationship
    # event = relationship("Event")

    __table_args__ = (
        UniqueConstraint("event_id", "wikipedia_page_title", name="uq_story_allowlist"),
    )

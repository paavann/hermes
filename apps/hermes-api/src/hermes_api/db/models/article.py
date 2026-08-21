from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hermes_api.db.base import Base, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from hermes_api.db.models.event import Event
    from hermes_api.db.models.source import Source



class Article(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "articles"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))

    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    
    published_at: Mapped[Optional[datetime]] = mapped_column()
    ingested_at: Mapped[datetime] = mapped_column(server_default="now()")
    created_at: Mapped[datetime] = mapped_column(server_default="now()")

    event: Mapped["Event"] = relationship(back_populates="articles")
    source: Mapped["Source"] = relationship(back_populates="articles")

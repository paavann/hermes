from sqlalchemy import Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from hermes_db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class GeocodeCache(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "geocode_cache"

    location_name: Mapped[str] = mapped_column(Text, unique=True, index=True)

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    display_name: Mapped[str | None] = mapped_column(Text)

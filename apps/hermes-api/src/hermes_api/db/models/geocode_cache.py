from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from hermes_api.db.base import Base, UUIDPrimaryKeyMixin


class GeocodeCache(Base, UUIDPrimaryKeyMixin):
    """DB-backed cache for geocoding results to avoid rate limits."""
    __tablename__ = "geocode_cache"

    # Normalized location name (lowercase, stripped)
    location_name: Mapped[str] = mapped_column(Text, unique=True, index=True)
    
    # Nullable fields to allow caching negative/not-found results
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    display_name: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

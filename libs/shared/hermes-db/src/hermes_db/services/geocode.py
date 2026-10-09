import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.models.geocode_cache import GeocodeCache


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GeocodeCacheEntry:
    location_name: str
    latitude: float | None
    longitude: float | None
    display_name: str | None


class GeocodeCacheService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


    async def get_by_location_name(
        self, location_name: str
    ) -> GeocodeCacheEntry | None:
        norm_key = location_name.strip().lower()
        stmt = select(GeocodeCache).where(GeocodeCache.location_name == norm_key)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return GeocodeCacheEntry(
            location_name=row.location_name,
            latitude=row.latitude,
            longitude=row.longitude,
            display_name=row.display_name,
        )


    async def save_geocode_result(
        self,
        location_name: str,
        latitude: float | None,
        longitude: float | None,
        display_name: str | None,
    ) -> GeocodeCacheEntry:
        norm_key = location_name.strip().lower()
        stmt = (
            pg_insert(GeocodeCache)
            .values(
                location_name=norm_key,
                latitude=latitude,
                longitude=longitude,
                display_name=display_name,
            )
            .on_conflict_do_nothing(index_elements=["location_name"])
        )
        await self._session.execute(stmt)
        await self._session.commit()

        existing = await self.get_by_location_name(norm_key)
        if existing is None:
            raise RuntimeError(
                f"geocode_cache row missing after upsert for location '{norm_key}'."
            )

        return existing

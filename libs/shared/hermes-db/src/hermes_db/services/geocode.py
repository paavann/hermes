import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_db.models.geocode_cache import GeocodeCache


logger = logging.getLogger(__name__)



class GeocodeCacheService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


    async def get_by_location_name(self, location_name: str) -> GeocodeCache | None:
        norm_key = location_name.strip().lower()
        stmt = select(GeocodeCache).where(GeocodeCache.location_name == norm_key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


    async def save_geocode_result(
        self,
        location_name: str,
        latitude: float | None, longitude: float | None,
        display_name: str | None
    ) -> GeocodeCache:
        norm_key = location_name.strip().lower()
        cache_entry = GeocodeCache(
            location_name=norm_key,
            latitude=latitude,
            longitude=longitude,
            display_name=display_name,
        )
        self._session.add(cache_entry)
        await self._session.commit()
        return cache_entry

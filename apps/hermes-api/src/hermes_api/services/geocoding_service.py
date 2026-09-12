import asyncio
import logging
import httpx
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.core.config import settings
from hermes_api.db.models.geocode_cache import GeocodeCache


logger = logging.getLogger(__name__)
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"




@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float
    display_name: str





class GeocodingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._lock: asyncio.Lock = asyncio.Lock()


    async def geocode(self, location_name: str) -> Optional[GeocodingResult]:
        norm_cache_key = location_name.strip().lower()
        
        # 1. Check DB Cache
        stmt = select(GeocodeCache).where(GeocodeCache.location_name == norm_cache_key)
        result = await self.session.execute(stmt)
        cached = result.scalar_one_or_none()
        
        if cached:
            logger.debug(f"geocoding db cache hit: {location_name}")
            # Support for negative caching (not found)
            if cached.latitude is None or cached.longitude is None:
                return None
            return GeocodingResult(
                latitude=cached.latitude,
                longitude=cached.longitude,
                display_name=cached.display_name or location_name,
            )
            
        # 2. Call API on cache miss
        api_result = await self._call_nominatim(location_name)
        
        # 3. Save to DB Cache
        new_cache = GeocodeCache(
            location_name=norm_cache_key,
            latitude=api_result.latitude if api_result else None,
            longitude=api_result.longitude if api_result else None,
            display_name=api_result.display_name if api_result else None,
        )
        self.session.add(new_cache)
        await self.session.commit()
        
        return api_result


    async def _call_nominatim(self, location_name: str) -> Optional[GeocodingResult]:
        async with self._lock:
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        NOMINATIM_SEARCH_URL,
                        params={
                            "q": location_name,
                            "format": "jsonv2",
                            "limit": 1,
                        },
                        headers={ "User-Agent": settings.NOMINATIM_USER_AGENT },
                        timeout=10.0,
                    )
                    res.raise_for_status()
                results = res.json()
                if not results:
                    logger.warning(f"no geocoding results for: {location_name}")
                    return None
                else:
                    first = results[0]
                    result = GeocodingResult(
                        latitude=float(first["lat"]),
                        longitude=float(first["lon"]),
                        display_name=first.get("display_name", location_name),
                    )
                    logger.info(f"geocoded '{location_name}' -> ({result.latitude}, {result.longitude})")
                    return result
            except httpx.HTTPError as e:
                logger.exception(f"failed to geocode '{location_name}'")
                return None
            except (KeyError, ValueError, IndexError):
                logger.exception(f"failed to parse nominatim response for: {location_name}")
                return None
            finally:
                await asyncio.sleep(1.0)



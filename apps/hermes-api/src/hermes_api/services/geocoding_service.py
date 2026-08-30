import asyncio
import logging
import httpx
from dataclasses import dataclass
from typing import Optional
from hermes_api.core.config import settings


logger = logging.getLogger(__name__)
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"




@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float
    display_name: str





class GeocodingService:
    def __init__(self) -> None:
        self._cache: dict[str, Optional[GeocodingResult]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()


    async def geocode(self, location_name: str) -> Optional[GeocodingResult]:
        norm_cache_key = location_name.strip().lower()
        if norm_cache_key in self._cache:
            logger.debug(f"geocoding cache hit: {location_name}")
            return self._cache[norm_cache_key]
        else:
            result = await self._call_nominatim(location_name)
            self._cache[norm_cache_key] = result
            return result


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


    @property
    def cache_size(self) -> int:
        return len(self._cache)

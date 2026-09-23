import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, Union

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.core.config import settings
from hermes_api.db.models.geocode_cache import GeocodeCache

logger = logging.getLogger(__name__)
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"

# Shared across all GeocodingService instances to enforce strict global rate limits
_nominatim_lock = asyncio.Lock()
_last_request_time: float = 0.0
_MIN_REQUEST_INTERVAL: float = 1.5  # seconds (OSM permits max 1 req/s; 1.5s absorbs latency jitter)


@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float
    display_name: str


class _NotFoundSentinel:
    """Sentinel indicating Nominatim returned a valid 200 OK with 0 results."""
    pass


_NOT_FOUND = _NotFoundSentinel()


class GeocodingService:
    def __init__(self) -> None:
        self._lock = _nominatim_lock

    async def geocode(self, session: AsyncSession, location_name: str) -> Optional[GeocodingResult]:
        norm_cache_key = location_name.strip().lower()

        stmt = select(GeocodeCache).where(GeocodeCache.location_name == norm_cache_key)
        result = await session.execute(stmt)
        cached = result.scalar_one_or_none()
        if cached:
            if cached.latitude is None or cached.longitude is None:
                return None
            return GeocodingResult(
                latitude=cached.latitude,
                longitude=cached.longitude,
                display_name=cached.display_name or location_name,
            )

        res = await self._call_nominatim(location_name)
        if isinstance(res, GeocodingResult):
            new_cache = GeocodeCache(
                location_name=norm_cache_key,
                latitude=res.latitude,
                longitude=res.longitude,
                display_name=res.display_name,
            )
            session.add(new_cache)
            await session.commit()
            return res
        elif res is _NOT_FOUND:
            # Only cache negative results when Nominatim responded 200 OK with no results
            new_cache = GeocodeCache(
                location_name=norm_cache_key,
                latitude=None,
                longitude=None,
                display_name=None,
            )
            session.add(new_cache)
            await session.commit()
            return None
        else:
            # Transient failure (HTTP 429, timeout, network error) - DO NOT poison cache
            return None

    async def _call_nominatim(
        self, location_name: str, max_retries: int = 3
    ) -> Union[GeocodingResult, _NotFoundSentinel, None]:
        global _last_request_time

        async with _nominatim_lock:
            for attempt in range(max_retries):
                # Enforce OSM rate limit: minimum 1.5s interval between requests
                now = time.monotonic()
                elapsed = now - _last_request_time
                if elapsed < _MIN_REQUEST_INTERVAL:
                    await asyncio.sleep(_MIN_REQUEST_INTERVAL - elapsed)

                try:
                    async with httpx.AsyncClient() as client:
                        res = await client.get(
                            NOMINATIM_SEARCH_URL,
                            params={
                                "q": location_name,
                                "format": "jsonv2",
                                "limit": 1,
                            },
                            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                            timeout=10.0,
                        )
                        _last_request_time = time.monotonic()

                        if res.status_code == 429:
                            retry_after_str = res.headers.get("Retry-After")
                            backoff = (
                                float(retry_after_str)
                                if retry_after_str and retry_after_str.isdigit()
                                else (5.0 * (2 ** attempt))
                            )
                            logger.warning(
                                "Nominatim 429 Too Many Requests for '%s'. Backing off for %.1fs (attempt %d/%d).",
                                location_name,
                                backoff,
                                attempt + 1,
                                max_retries,
                            )
                            await asyncio.sleep(backoff)
                            continue

                        res.raise_for_status()

                    results = res.json()
                    if not results:
                        logger.warning("No geocoding results found for: '%s'.", location_name)
                        return _NOT_FOUND

                    first = results[0]
                    result = GeocodingResult(
                        latitude=float(first["lat"]),
                        longitude=float(first["lon"]),
                        display_name=first.get("display_name", location_name),
                    )
                    logger.info("Geocoded '%s' -> (%s, %s).", location_name, result.latitude, result.longitude)
                    return result

                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Nominatim HTTP status error %s for '%s' (attempt %d/%d).",
                        exc.response.status_code,
                        location_name,
                        attempt + 1,
                        max_retries,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2.0 * (attempt + 1))
                    else:
                        return None
                except httpx.HTTPError as exc:
                    logger.warning(
                        "Nominatim network/connection error for '%s' (attempt %d/%d): %s",
                        location_name,
                        attempt + 1,
                        max_retries,
                        exc,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2.0 * (attempt + 1))
                    else:
                        return None
                except (KeyError, ValueError, IndexError):
                    logger.exception("Failed to parse Nominatim response for '%s'.", location_name)
                    return None

            logger.error("Failed to geocode '%s' after %d attempts.", location_name, max_retries)
            return None

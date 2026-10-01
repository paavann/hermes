import asyncio
import logging
import re
import time
from dataclasses import dataclass
import httpx
from hermes_db.services import GeocodeCacheService
from hermes_worker.core.config import settings


logger = logging.getLogger(__name__)
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float
    display_name: str


def clean_location_name(location: str) -> str | None:
    if not location or not location.strip():
        return None

    location = location.strip()
    eg_match = re.search(
        r"\((?:e\.g\.,?\s*|including\s*)([^\),]+)", location, re.IGNORECASE
    )
    location = (
        eg_match.group(1).strip()
        if eg_match
        else re.sub(r"\(.*?\)", "", location).strip()
    )
    location = location.strip(" ,.-")
    if len(location) < 2 or location.lower() in [
        "multiple cities",
        "multiple locations",
        "nationwide",
        "various locations",
        "various cities",
        "global",
        "worldwide",
    ]:
        return None
    return location


class GeocodingService:
    def __init__(self, cache_service: GeocodeCacheService) -> None:
        self._cache_service = cache_service
        self._lock = asyncio.Lock()
        self._last_req_time: float = 0.0
        self._min_interval: float = 1.0
        self._in_flight: dict[str, asyncio.Future[GeocodingResult | None]] = {}
        self._consecutive_rate_limits: int = 0
        self._circuit_open_until: float = 0.0

    async def _call_nominatim(self, location_name: str) -> GeocodingResult | None:
        async with self._lock:
            now = time.monotonic()
            if now < self._circuit_open_until:
                remaining = self._circuit_open_until - now
                logger.warning(
                    "geocoding circuit open; skipping Nominatim call for '%s' (cooling down for %.1fs).",
                    location_name,
                    remaining,
                )
                return None

            elapsed = now - self._last_req_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)

            params = {
                "q": location_name,
                "format": "jsonv2",
                "limit": 1,
            }
            headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        NOMINATIM_SEARCH_URL,
                        params=params,
                        headers=headers,
                        timeout=10.0,
                    )
                self._last_req_time = time.monotonic()

                if res.status_code in (429, 403):
                    self._consecutive_rate_limits += 1
                    logger.warning(
                        "nominatim responded with %d for '%s' (streak=%d).",
                        res.status_code,
                        location_name,
                        self._consecutive_rate_limits,
                    )
                    if self._consecutive_rate_limits >= 3:
                        cooldown = min(
                            60.0, 10.0 * (2 ** (self._consecutive_rate_limits - 3))
                        )
                        self._circuit_open_until = time.monotonic() + cooldown
                        logger.error("geocoding circuit opened for %.1fs.", cooldown)
                    return None

                res.raise_for_status()
                self._consecutive_rate_limits = 0
            except Exception:
                logger.exception("nominatim request failed for '%s'.", location_name)
                return None

            data = res.json()
            if not data:
                return None
            else:
                first = data[0]
                try:
                    return GeocodingResult(
                        latitude=float(first["lat"]),
                        longitude=float(first["lon"]),
                        display_name=first.get("display_name", location_name),
                    )
                except KeyError, ValueError, TypeError:
                    logger.exception(
                        "malformed nominatim response for '%s': %s",
                        location_name,
                        first,
                    )
                    return None

    async def geocode(self, location_name: str) -> GeocodingResult | None:
        cleaned = clean_location_name(location_name)
        if not cleaned:
            return None

        normalized_key = cleaned.strip().lower()
        cached = await self._cache_service.get_by_location_name(normalized_key)
        if cached is not None:
            if cached.latitude is None or cached.longitude is None:
                return None
            return GeocodingResult(
                latitude=cached.latitude,
                longitude=cached.longitude,
                display_name=cached.display_name or location_name,
            )

        loop = asyncio.get_running_loop()
        if normalized_key in self._in_flight:
            return await self._in_flight[normalized_key]

        future = loop.create_future()
        self._in_flight[normalized_key] = future
        try:
            result = await self._call_nominatim(cleaned)
            if result:
                await self._cache_service.save_geocode_result(
                    location_name=normalized_key,
                    latitude=result.latitude,
                    longitude=result.longitude,
                    display_name=result.display_name,
                )
            else:
                await self._cache_service.save_geocode_result(
                    location_name=normalized_key,
                    latitude=None,
                    longitude=None,
                    display_name=None,
                )
            future.set_result(result)
            return result
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            self._in_flight.pop(normalized_key, None)

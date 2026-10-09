import asyncio
import logging
import re
import time
import httpx
from dataclasses import dataclass
from typing import Protocol


logger = logging.getLogger(__name__)

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float
    display_name: str


class _NotFoundSentinel:
    pass


_NOT_FOUND = _NotFoundSentinel()


class GeocodeCacheEntry(Protocol):
    @property
    def latitude(self) -> float | None: ...

    @property
    def longitude(self) -> float | None: ...

    @property
    def display_name(self) -> str | None: ...


class GeocodeCacheProtocol(Protocol):
    async def get_by_location_name(
        self, location_name: str
    ) -> GeocodeCacheEntry | None: ...

    async def save_geocode_result(
        self,
        location_name: str,
        latitude: float | None,
        longitude: float | None,
        display_name: str | None,
    ) -> object: ...


def clean_location_name(loc: str) -> str | None:
    """Sanitize location names extracted from news articles or Wikipedia.

    Args:
        loc: Raw location string.

    Returns:
        Sanitized location name or None if unlocatable.
    """
    if not loc or not loc.strip():
        return None

    loc = loc.strip()
    eg_match = re.search(
        r"\((?:e\.g\.,?\s*|including\s*)([^\),]+)", loc, re.IGNORECASE
    )
    loc = (
        eg_match.group(1).strip()
        if eg_match
        else re.sub(r"\(.*?\)", "", loc).strip()
    )

    loc = loc.strip(" ,.-")
    if len(loc) < 2 or loc.lower() in {
        "multiple cities",
        "multiple locations",
        "various",
        "various locations",
        "various cities",
        "several locations",
        "nationwide",
        "unknown",
        "global",
        "worldwide",
    }:
        return None
    return loc


class NominatimResilienceManager:
    """Thread-safe rate-limiter and circuit breaker for Nominatim OSM API."""

    def __init__(
        self,
        min_request_interval: float = 1.0,
        circuit_cooldown_seconds: float = 120.0,
    ) -> None:
        self.min_request_interval = min_request_interval
        self.circuit_cooldown_seconds = circuit_cooldown_seconds
        self.last_request_time: float = 0.0
        self.circuit_open_until: float = 0.0
        self._lock = asyncio.Lock()

    def is_circuit_open(self) -> tuple[bool, float]:
        now = time.monotonic()
        if now < self.circuit_open_until:
            return True, self.circuit_open_until - now
        return False, 0.0


    def trip_circuit_breaker(self) -> None:
        self.circuit_open_until = time.monotonic() + self.circuit_cooldown_seconds


    async def enforce_pacing(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_request_time
            if elapsed < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - elapsed)
            self.last_request_time = time.monotonic()


class GeocodingService:
    """Resilient geocoding service backed by OpenStreetMap Nominatim and optional cache."""

    def __init__(
        self,
        cache_service: GeocodeCacheProtocol | None = None,
        user_agent: str = "hermes-geocoder/1.0",
        min_interval: float = 1.0,
        circuit_cooldown: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._cache = cache_service
        self._user_agent = user_agent
        self._resilience = NominatimResilienceManager(
            min_request_interval=min_interval,
            circuit_cooldown_seconds=circuit_cooldown,
        )
        self._client = client
        self._in_flight: dict[str, asyncio.Future[GeocodingResult | None]] = {}


    async def geocode(self, location_name: str) -> GeocodingResult | None:
        """Geocode a location name into latitude and longitude coordinates.

        Args:
            location_name: Free-text place name.

        Returns:
            GeocodingResult if resolved, None otherwise.
        """
        cleaned = clean_location_name(location_name)
        if not cleaned:
            return None

        norm_key = cleaned.strip().lower()
        if self._cache is not None:
            cached = await self._cache.get_by_location_name(norm_key)
            if cached is not None:
                if cached.latitude is None or cached.longitude is None:
                    return None
                return GeocodingResult(
                    latitude=cached.latitude,
                    longitude=cached.longitude,
                    display_name=cached.display_name or cleaned,
                )

        loop = asyncio.get_running_loop()
        if norm_key in self._in_flight:
            return await self._in_flight[norm_key]

        future = loop.create_future()
        self._in_flight[norm_key] = future
        try:
            res = await self._call_nominatim(cleaned)
            if isinstance(res, GeocodingResult):
                if self._cache is not None:
                    await self._cache.save_geocode_result(
                        location_name=norm_key,
                        latitude=res.latitude,
                        longitude=res.longitude,
                        display_name=res.display_name,
                    )
                future.set_result(res)
                return res
            elif res is _NOT_FOUND:
                if self._cache is not None:
                    await self._cache.save_geocode_result(
                        location_name=norm_key,
                        latitude=None,
                        longitude=None,
                        display_name=None,
                    )
                future.set_result(None)
                return None
            else:
                future.set_result(None)
                return None
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            self._in_flight.pop(norm_key, None)


    async def _call_nominatim(
        self, location_name: str, max_retries: int = 3
    ) -> GeocodingResult | _NotFoundSentinel | None:
        """Execute HTTP request to Nominatim API with retries and circuit breaker."""
        circuit_open, remaining = self._resilience.is_circuit_open()
        if circuit_open:
            logger.warning(
                "nominatim circuit breaker active (%.0fs remaining). skipping geocoding for '%s'.",
                remaining,
                location_name,
            )
            return None

        last_was_429 = False
        params = {
            "q": location_name,
            "format": "jsonv2",
            "limit": 1,
        }
        headers = {"User-Agent": self._user_agent}

        for attempt in range(max_retries):
            await self._resilience.enforce_pacing()

            try:
                if self._client is not None:
                    res = await self._client.get(
                        NOMINATIM_SEARCH_URL,
                        params=params,
                        headers=headers,
                        timeout=10.0,
                    )
                else:
                    async with httpx.AsyncClient() as client:
                        res = await client.get(
                            NOMINATIM_SEARCH_URL,
                            params=params,
                            headers=headers,
                            timeout=10.0,
                        )

                if res.status_code == 429:
                    last_was_429 = True
                    retry_after_str = res.headers.get("Retry-After")
                    raw_retry = (
                        float(retry_after_str)
                        if retry_after_str and retry_after_str.isdigit()
                        else 0.0
                    )
                    backoff = max(raw_retry, 5.0 * (2**attempt))
                    logger.warning(
                        "nominatim 429 too many requests for '%s'. backing off for %.1fs (attempt %d/%d).",
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
                    logger.warning(
                        "no geocoding results found for '%s'.", location_name
                    )
                    return _NOT_FOUND

                first = results[0]
                result = GeocodingResult(
                    latitude=float(first["lat"]),
                    longitude=float(first["lon"]),
                    display_name=first.get("display_name", location_name),
                )
                logger.info(
                    "geocoded '%s' -> (%s, %s).",
                    location_name,
                    result.latitude,
                    result.longitude,
                )
                return result

            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "nominatim http status error %s for '%s' (attempt %d/%d).",
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
                    "nominatim network/connection error for '%s' (attempt %d/%d): %s.",
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
                logger.exception(
                    "failed to parse nominatim response for '%s'.",
                    location_name,
                )
                return None

        if last_was_429:
            self._resilience.trip_circuit_breaker()
            logger.error(
                "nominatim 429 persistent for '%s' after %d attempts. tripping circuit breaker for %ds.",
                location_name,
                max_retries,
                int(self._resilience.circuit_cooldown_seconds),
            )
        else:
            logger.error(
                "failed to geocode '%s' after %d attempts.",
                location_name,
                max_retries,
            )

        return None

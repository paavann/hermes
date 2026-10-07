import asyncio
import logging
import re
import time
from dataclasses import dataclass
import httpx
from hermes_db.services import GeocodeCacheService
from hermes_api.core.config import settings


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


def clean_location_name(loc: str) -> str | None:
    """Sanitize location names extracted from news articles or Wikipedia.

    Extracts concrete place names from messy inputs like 'Multiple cities (e.g., Sanaa, Taiz)'
    or 'Sanaa (mosque)' or 'Yemen (nationwide)'.
    """
    if not loc or not loc.strip():
        return None

    loc = loc.strip()
    eg_match = re.search(r"\((?:e\.g\.,?\s*|including\s*)([^\),]+)", loc, re.IGNORECASE)
    loc = eg_match.group(1).strip() if eg_match else re.sub(r"\(.*?\)", "", loc).strip()

    loc = loc.strip(" ,.-")
    if len(loc) < 2 or loc.lower() in [
        "multiple cities",
        "various",
        "various locations",
        "nationwide",
        "unknown",
        "several locations",
        "global",
    ]:
        return None
    return loc


class NominatimResilienceManager:
    def __init__(
        self, min_request_interval: float = 1.5, circuit_cooldown_seconds: float = 120.0
    ) -> None:
        self.min_request_interval = min_request_interval
        self.circuit_cooldown_seconds = circuit_cooldown_seconds
        self.last_request_time: float = 0.0
        self.circuit_open_until: float = 0.0
        self.lock = asyncio.Lock()

    def is_circuit_open(self) -> tuple[bool, float]:
        now = time.monotonic()
        if now < self.circuit_open_until:
            return True, self.circuit_open_until - now
        return False, 0.0

    def trip_circuit_breaker(self) -> None:
        self.circuit_open_until = time.monotonic() + self.circuit_cooldown_seconds

    async def enforce_pacing(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_request_time
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.monotonic()


class GeocodingService:
    _resilience = NominatimResilienceManager()

    def __init__(self, cache_service: GeocodeCacheService) -> None:
        self._cache_service = cache_service

    async def geocode(self, location_name: str) -> GeocodingResult | None:
        cleaned = clean_location_name(location_name)
        if not cleaned:
            return None

        cached = await self._cache_service.get_by_location_name(cleaned)

        if cached:
            if cached.latitude is None or cached.longitude is None:
                return None
            return GeocodingResult(
                latitude=cached.latitude,
                longitude=cached.longitude,
                display_name=cached.display_name or cleaned,
            )

        res = await self._call_nominatim(cleaned)
        if isinstance(res, GeocodingResult):
            await self._cache_service.save_geocode_result(
                location_name=cleaned,
                latitude=res.latitude,
                longitude=res.longitude,
                display_name=res.display_name,
            )
            return res
        elif res is _NOT_FOUND:
            # Cache negative result only when Nominatim returned 200 OK with 0 results
            await self._cache_service.save_geocode_result(
                location_name=cleaned,
                latitude=None,
                longitude=None,
                display_name=None,
            )
            return None
        else:
            # Transient failure (HTTP 429, timeout, network error) - DO NOT poison cache
            return None

    async def _call_nominatim(
        self, location_name: str, max_retries: int = 3
    ) -> GeocodingResult | _NotFoundSentinel | None:
        async with self._resilience.lock:
            circuit_open, remaining = self._resilience.is_circuit_open()
            if circuit_open:
                logger.warning(
                    "Nominatim circuit breaker active (%.0fs remaining). Skipping geocoding for '%s'.",
                    remaining,
                    location_name,
                )
                return None

            last_was_429 = False

            async with httpx.AsyncClient() as client:
                for attempt in range(max_retries):
                    await self._resilience.enforce_pacing()

                    try:
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
                            logger.warning(
                                "No geocoding results found for: '%s'.", location_name
                            )
                            return _NOT_FOUND

                        first = results[0]
                        result = GeocodingResult(
                            latitude=float(first["lat"]),
                            longitude=float(first["lon"]),
                            display_name=first.get("display_name", location_name),
                        )
                        logger.info(
                            "Geocoded '%s' -> (%s, %s).",
                            location_name,
                            result.latitude,
                            result.longitude,
                        )
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
                        logger.exception(
                            "failed to parse Nominatim response for '%s'.",
                            location_name,
                        )
                        return None

            if last_was_429:
                self._resilience.trip_circuit_breaker()
                logger.error(
                    "Nominatim 429 persistent for '%s' after %d attempts. Tripping circuit breaker for %ds.",
                    location_name,
                    max_retries,
                    int(self._resilience.circuit_cooldown_seconds),
                )
            else:
                logger.error(
                    "Failed to geocode '%s' after %d attempts.",
                    location_name,
                    max_retries,
                )

            return None

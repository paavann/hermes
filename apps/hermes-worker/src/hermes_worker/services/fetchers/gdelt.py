import json
import logging
from datetime import datetime
from urllib.parse import urlparse
import httpx
from hermes_ai.utils.rate_limiter import TbRateLimiter
from hermes_db.services.source import DueSource
from hermes_worker.core.config import settings
from hermes_worker.services.fetchers.base import BaseArticleFetcher, ParsedArticle


logger = logging.getLogger(__name__)

GDELT_DOC_API_URL: str = "https://api.gdeltproject.org/api/v2/doc/doc"
_DEFAULT_GDELT_LIMITER = TbRateLimiter(req_per_min=12, max_burst=1.0)


def _parse_gdelt_date(date_str: str) -> datetime | None:
    """Parse GDELT date format string into a datetime object.

    Args:
        date_str: Formatted date string from GDELT DOC API.

    Returns:
        Parsed datetime or None if format is unrecognized.
    """
    if not date_str:
        return None
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None


def _extract_domain(url: str | None) -> str:
    """Extract clean domain name from URL.

    Args:
        url: Full URL string.

    Returns:
        Stripped domain name.
    """
    if not url:
        return ""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    if domain.startswith("www."):
        domain = domain[4:]
    return domain.split("/")[0].strip()


class GDELTFetcher(BaseArticleFetcher):
    """Fetcher for wire articles via GDELT 2.0 DOC API."""

    def __init__(
        self,
        rate_limiter: TbRateLimiter | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize GDELTFetcher.

        Args:
            rate_limiter: Optional token bucket rate limiter with burst control.
            client: Optional httpx.AsyncClient instance.
        """
        self._limiter = rate_limiter or _DEFAULT_GDELT_LIMITER
        self._client = client


    async def fetch_articles(self, source: DueSource) -> list[ParsedArticle]:
        """Fetch and parse wire articles from GDELT 2.0 API.

        Args:
            source: DueSource configuration.

        Returns:
            List of parsed articles.
        """
        if self._limiter.is_circuit_open():
            logger.warning(
                "gdelt circuit breaker is open. skipping source '%s'.",
                source.name,
            )
            return []

        domain = _extract_domain(source.url)
        if not domain:
            logger.warning(
                "cannot determine domain for GDELT source '%s'. skipping source.",
                source.name,
            )
            return []

        await self._limiter.acquire()

        params = {
            "query": f"domain:{domain}",
            "mode": "artlist",
            "maxrecords": "50",
            "format": "json",
            "sort": "datedesc",
        }

        try:
            if self._client:
                res = await self._client.get(
                    GDELT_DOC_API_URL,
                    params=params,
                    timeout=30.0,
                    headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                )
            else:
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        GDELT_DOC_API_URL,
                        params=params,
                        timeout=30.0,
                        headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                    )

            if res.status_code in (429, 403):
                self._limiter.trip_circuit_breaker()
                logger.warning(
                    "gdelt returned status %s for source '%s'. circuit breaker tripped.",
                    res.status_code,
                    source.name,
                )
                return []

            res.raise_for_status()
        except httpx.TimeoutException:
            logger.warning(
                "timeout querying gdelt for source '%s'. skipping source.",
                source.name,
            )
            return []
        except httpx.HTTPError as exc:
            logger.warning(
                "failed to fetch gdelt articles for source '%s': %s.",
                source.name,
                exc,
            )
            return []

        try:
            data = res.json()
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "invalid json from gdelt for source '%s'.",
                source.name,
            )
            return []

        if not isinstance(data, dict):
            return []

        raw_articles = data.get("articles")
        if not isinstance(raw_articles, list):
            return []

        articles: list[ParsedArticle] = []
        for item in raw_articles:
            if not isinstance(item, dict):
                continue
            title_val = item.get("title")
            url_val = item.get("url")
            title = str(title_val).strip() if title_val else ""
            url = str(url_val).strip() if url_val else ""
            if not title or not url:
                continue

            seendate_val = item.get("seendate")
            seendate = str(seendate_val).strip() if seendate_val else ""
            pub_at = _parse_gdelt_date(seendate)

            country_val = item.get("sourcecountry")
            source_country = str(country_val).strip() if country_val else None

            articles.append(
                ParsedArticle(
                    title=title,
                    url=url,
                    description=title,
                    content=None,
                    published_at=pub_at,
                    source_country=source_country,
                )
            )

        logger.info(
            "fetched %d articles from GDELT for %s.",
            len(articles),
            source.name,
        )
        return articles

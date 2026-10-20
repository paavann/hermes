import logging
from collections.abc import Mapping
from datetime import datetime
import feedparser
import httpx
from hermes_db.services.source import DueSource
from hermes_worker.core.config import settings
from hermes_worker.services.fetchers.base import BaseArticleFetcher, ParsedArticle


logger = logging.getLogger(__name__)


def _parse_date(entry: Mapping[str, object]) -> datetime | None:
    parsed_time = entry.get("published_parsed")
    if parsed_time and isinstance(parsed_time, (tuple, list)):
        try:
            return datetime(*parsed_time[:6])
        except (ValueError, TypeError):
            return None
    return None


def _extract_content(entry: Mapping[str, object]) -> str | None:
    content_list = entry.get("content", [])
    if isinstance(content_list, list) and content_list:
        first = content_list[0]
        if isinstance(first, dict):
            val = first.get("value", "")
            if isinstance(val, str) and val.strip():
                return val.strip()

    encoded = entry.get("content_encoded", "")
    if isinstance(encoded, str) and encoded.strip():
        return encoded.strip()

    return None


async def fetch_feed(feed_url: str) -> list[ParsedArticle]:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                feed_url,
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
            )
            res.raise_for_status()
    except httpx.TimeoutException:
        logger.warning(
            "timeout fetching RSS feed %s (> 30s). skipping source.", feed_url
        )
        return []
    except httpx.HTTPError as exc:
        logger.warning("failed to fetch RSS feed %s: %s.", feed_url, exc)
        return []

    feed = feedparser.parse(res.text)
    if feed.bozo and not feed.bozo_exception:
        logger.warning("malformed feed with no entries: %s.", feed_url)
        return []

    articles: list[ParsedArticle] = []
    for entry in feed.entries:
        title_val = entry.get("title")
        title = title_val.strip() if isinstance(title_val, str) else ""

        url_val = entry.get("link")
        url = url_val.strip() if isinstance(url_val, str) else ""
        if not title or not url:
            continue

        desc_val = entry.get("summary")
        description = desc_val.strip() if isinstance(desc_val, str) else ""
        content = _extract_content(entry)
        pub_at = _parse_date(entry)
        articles.append(
            ParsedArticle(
                title=title,
                url=url,
                description=description,
                content=content,
                published_at=pub_at,
            )
        )

    logger.info("fetched %d articles from %s.", len(articles), feed_url)
    return articles


class RSSFetcher(BaseArticleFetcher):
    async def fetch_articles(self, source: DueSource) -> list[ParsedArticle]:
        if not source.feed_url:
            logger.warning(
                "source '%s' has no feed_url configured for RSS fetching.",
                source.name,
            )
            return []

        return await fetch_feed(source.feed_url)

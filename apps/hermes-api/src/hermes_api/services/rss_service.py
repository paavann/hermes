from pydantic import computed_field
from pydantic import BaseModel
from feedparser.datetimes import _parse_date
import feedparser
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional
from hermes_api.core.config import settings


logger = logging.getLogger(__name__)
MAX_CONTENT_WORDS: int = 500





def _parse_date(entry: dict) -> Optional[datetime]:
    parsed_time = entry.get("published_parsed")
    if parsed_time:
        try:
            return datetime(*parsed_time[:6])
        except (ValueError, TypeError):
            return None
    return None


def _truncate_to_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    else:
        return " ".join(words[:max_words]) + "..."


def _extract_content(entry: dict) -> Optional[str]:
    content_list = entry.get("content", [])
    if content_list:
        return content_list[0].get("value", "").strip() or None
    
    encoded = entry.get("content_encoded", "")
    if encoded:
        return encoded.strip() or None

    return None





class ParsedArticle(BaseModel):
    title: str
    url: str
    description: str
    content: Optional[str] = None
    published_at: Optional[datetime] = None

    @computed_field
    @property
    def text_for_ai(self) -> str:
        if self.content:
            return _truncate_to_words(self.content, MAX_CONTENT_WORDS)
        else:
            return self.description





async def fetch_feed(feed_url: str) -> list[ParsedArticle]:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                feed_url,
                timeout=30.0,
                follow_redirects=True,
                headers={ "User-Agent": settings.NOMINATIM_USER_AGENT },
            )
            res.raise_for_status()
    except httpx.HTTPError as e:
        logger.exception(f"failed to fetch RSS feed: {feed_url}")
        return []

    feed = feedparser.parse(res.text)
    if feed.bozo and not feed.bozo_exception:
        logger.warning(f"malformed feed with no entries: {feed_url}")
        return []


    articles: list[ParsedArticle] = []
    for entry in feed.entries:
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()

        if not title or not url:
            continue
        else:
            description = entry.get("summary", "").strip()
            content = _extract_content(entry)
            published_at = _parse_date(entry)
            articles.append(
                ParsedArticle(
                    title=title,
                    url=url,
                    description=description,
                    content=content,
                    published_at=published_at,
                )
            )


    logger.info(f"parsed {len(articles)} articles from {feed_url}")
    return articles
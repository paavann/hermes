import logging
import xml.etree.ElementTree as ET
from datetime import datetime
import httpx
import trafilatura
from hermes_db.services.source import DueSource
from hermes_worker.core.config import settings
from hermes_worker.services.fetchers.base import BaseArticleFetcher, ParsedArticle


logger = logging.getLogger(__name__)


def _parse_sitemap_urls(xml_content: str, max_urls: int = 20) -> list[str]:
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return []

    urls: list[str] = []
    for elem in root.iter():
        if elem.tag.endswith("loc") and elem.text:
            url = elem.text.strip()
            if url.startswith(("http://", "https://")):
                urls.append(url)
                if len(urls) >= max_urls:
                    break
    return urls


def _extract_article_from_html(html: str, url: str) -> ParsedArticle | None:
    text = trafilatura.extract(html)
    if not text:
        return None

    meta = trafilatura.extract_metadata(html)
    title = (meta.title if meta and meta.title else "").strip()
    if not title:
        title = text.split("\n")[0][:120].strip()

    description = (meta.description if meta and meta.description else "").strip()
    if not description:
        description = text[:200].strip()

    pub_at: datetime | None = None
    if meta and meta.date:
        try:
            pub_at = datetime.fromisoformat(meta.date)
        except ValueError:
            pub_at = None

    return ParsedArticle(
        title=title,
        url=url,
        description=description,
        content=text,
        published_at=pub_at,
    )


class SitemapFetcher(BaseArticleFetcher):
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        max_articles: int = 20,
    ) -> None:
        self._client = client
        self._max_articles = max_articles

    async def fetch_articles(self, source: DueSource) -> list[ParsedArticle]:
        sitemap_url = source.feed_url
        if not sitemap_url:
            base_url = (source.url or "").rstrip("/")
            if not base_url:
                logger.warning(
                    "no URL or feed_url available for sitemap source '%s'.",
                    source.name,
                )
                return []
            sitemap_url = f"{base_url}/sitemap.xml"

        logger.info(
            "fetching sitemap for '%s' from %s.",
            source.name,
            sitemap_url,
        )

        try:
            if self._client:
                res = await self._client.get(
                    sitemap_url,
                    timeout=30.0,
                    follow_redirects=True,
                    headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                )
                res.raise_for_status()
                xml_text = res.text
            else:
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        sitemap_url,
                        timeout=30.0,
                        follow_redirects=True,
                        headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                    )
                    res.raise_for_status()
                    xml_text = res.text
        except httpx.HTTPError as exc:
            logger.warning(
                "failed to fetch sitemap for '%s' from %s: %s.",
                source.name,
                sitemap_url,
                exc,
            )
            return []

        urls = _parse_sitemap_urls(xml_text, max_urls=self._max_articles)
        if not urls:
            logger.warning(
                "no valid article URLs found in sitemap for '%s'.",
                source.name,
            )
            return []

        articles: list[ParsedArticle] = []
        for url in urls:
            try:
                if self._client:
                    html_res = await self._client.get(
                        url,
                        timeout=15.0,
                        follow_redirects=True,
                        headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                    )
                else:
                    async with httpx.AsyncClient() as client:
                        html_res = await client.get(
                            url,
                            timeout=15.0,
                            follow_redirects=True,
                            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                        )

                if html_res.status_code in (403, 429):
                    logger.warning(
                        "status %s received fetching %s. skipping.",
                        html_res.status_code,
                        url,
                    )
                    continue

                html_res.raise_for_status()
                article = _extract_article_from_html(html_res.text, url)
                if article:
                    articles.append(article)
            except httpx.HTTPError as exc:
                logger.warning("failed to fetch article page %s: %s.", url, exc)
                continue

        logger.info(
            "extracted %d articles from sitemap for '%s'.",
            len(articles),
            source.name,
        )
        return articles

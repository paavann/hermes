import logging
from hermes_db.services.source import DueSource
from hermes_worker.services.fetchers.base import BaseArticleFetcher, ParsedArticle
from hermes_worker.services.rss import fetch_feed


logger = logging.getLogger(__name__)


class RSSFetcher(BaseArticleFetcher):
    """Fetcher for standard XML RSS feeds."""

    async def fetch_articles(self, source: DueSource) -> list[ParsedArticle]:
        """Fetch articles from the source RSS feed URL.

        Args:
            source: DueSource configuration.

        Returns:
            List of parsed articles.
        """
        if not source.feed_url:
            logger.warning(
                "source '%s' has no feed_url configured for RSS fetching.",
                source.name,
            )
            return []

        return await fetch_feed(source.feed_url)

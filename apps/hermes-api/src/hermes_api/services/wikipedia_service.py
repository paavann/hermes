"""MediaWiki Action API client for Wikipedia content retrieval.

Provides two public functions:
- ``search_timeline_titles``: discover sub-page titles by ``intitle`` search.
- ``fetch_page_extracts``: fetch plain-text content for one or more pages,
  batched at up to 50 titles per request as per MediaWiki API constraints.

All requests include a descriptive ``User-Agent`` per Wikimedia's API etiquette
policy, mirroring the same courtesy already applied to the Nominatim integration.

No new third-party dependency is introduced; the existing ``httpx`` client is
reused throughout.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MEDIAWIKI_API_URL = "https://en.wikipedia.org/w/api.php"

# Wikimedia policy: every bot/application must identify itself.
# Format mirrors the Nominatim User-Agent already in use.
_USER_AGENT = (
    "hermes-api/1.0 (geospatial news aggregator; "
    "https://github.com/your-org/hermes; contact@hermes.example.com)"
)

# MediaWiki Action API hard cap for multi-title lookups.
_MAX_TITLES_PER_REQUEST = 50

# Shared timeout for all Wikipedia API calls (seconds).
_REQUEST_TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def search_timeline_titles(
    query: str,
    *,
    limit: int = 50,
) -> list[str]:
    """Search Wikipedia for pages whose title contains *query*.

    Uses the ``list=search`` action with ``srsearch=intitle:"..."`` to find
    pages whose title matches the supplied term.  Useful for discovering all
    date-range sub-articles that exist for a long-running story's timeline
    (e.g. "Timeline of the Israel–Gaza conflict").

    Args:
        query: The search string to match against page titles.
        limit: Maximum number of results to return (1–50, capped by API).

    Returns:
        An ordered list of page title strings, or an empty list on failure.
    """
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f'intitle:"{query}"',
        "srlimit": min(limit, _MAX_TITLES_PER_REQUEST),
        "srnamespace": "0",  # main (article) namespace only
        "format": "json",
        "formatversion": "2",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                MEDIAWIKI_API_URL,
                params=params,
                headers={"User-Agent": _USER_AGENT},
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()

        data = response.json()
        results: list[dict] = data.get("query", {}).get("search", [])
        titles = [r["title"] for r in results if "title" in r]
        logger.info(
            f"wikipedia search '{query}' returned {len(titles)} title(s)."
        )
        return titles

    except httpx.HTTPError:
        logger.exception(
            f"http error while searching wikipedia for '{query}'."
        )
        return []
    except (KeyError, ValueError):
        logger.exception(
            f"failed to parse wikipedia search response for '{query}'."
        )
        return []


async def fetch_page_extracts(
    titles: list[str],
) -> dict[str, Optional[str]]:
    """Fetch the plain-text content of one or more Wikipedia pages.

    Batches requests at ``_MAX_TITLES_PER_REQUEST`` titles per call to stay
    within MediaWiki's multi-title limit.  Uses ``prop=extracts&explaintext=1``
    so the returned text is plain prose (no wiki markup), suitable for direct
    LLM consumption.

    Args:
        titles: One or more Wikipedia page titles to fetch.  Duplicate titles
            are deduplicated before the request is sent.

        Returns:
            A dict mapping each title to its plain-text extract string.
            Pages that are missing, redirected away, or return empty content
            are mapped to ``None``.  Keys always match the requested titles
            (normalised casing may differ from what Wikipedia returns; the
            function resolves normalisation automatically).
    """
    if not titles:
        return {}

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique_titles: list[str] = []
    for t in titles:
        if t not in seen:
            seen.add(t)
            unique_titles.append(t)

    results: dict[str, Optional[str]] = {t: None for t in unique_titles}

    # Slice into batches of _MAX_TITLES_PER_REQUEST.
    batches = [
        unique_titles[i: i + _MAX_TITLES_PER_REQUEST]
        for i in range(0, len(unique_titles), _MAX_TITLES_PER_REQUEST)
    ]

    for batch in batches:
        batch_result = await _fetch_extracts_batch(batch)
        results.update(batch_result)

    non_null = sum(1 for v in results.values() if v is not None)
    logger.info(
        f"fetched extracts for {non_null}/{len(unique_titles)} wikipedia page(s)."
    )
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_extracts_batch(
    titles: list[str],
) -> dict[str, Optional[str]]:
    """Fetch plain-text extracts for a single batch of up to 50 titles.

    Args:
        titles: At most ``_MAX_TITLES_PER_REQUEST`` Wikipedia page titles.

    Returns:
        Partial results dict mapping each requested title to its extract
        string, or ``None`` if the page was missing or empty.
    """
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "titles": "|".join(titles),
        "format": "json",
        "formatversion": "2",
    }

    out: dict[str, Optional[str]] = {t: None for t in titles}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                MEDIAWIKI_API_URL,
                params=params,
                headers={"User-Agent": _USER_AGENT},
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()

        data = response.json()
        pages: list[dict] = data.get("query", {}).get("pages", [])

        # Build a normalisation map so we can match returned titles back to
        # whatever casing the caller used.  MediaWiki often returns titles
        # with different capitalisation than what was requested.
        normalised: dict[str, str] = {
            t.lower().replace("_", " "): t for t in titles
        }

        for page in pages:
            # A page_id of -1 means "page does not exist".
            if page.get("missing") or page.get("id", 0) == -1:
                continue

            returned_title: str = page.get("title", "")
            extract: str = page.get("extract", "").strip()

            if not extract:
                logger.debug(
                    f"wikipedia page '{returned_title}' returned an empty extract."
                )
                continue

            # Resolve returned title back to the caller's key.
            lookup = returned_title.lower().replace("_", " ")
            caller_key = normalised.get(lookup, returned_title)
            out[caller_key] = extract

    except httpx.HTTPError:
        logger.exception(
            f"http error fetching extracts for batch: {titles[:3]}..."
        )
    except (KeyError, ValueError):
        logger.exception(
            f"failed to parse extracts response for batch: {titles[:3]}..."
        )

    return out

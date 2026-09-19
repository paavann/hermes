import logging
import re
from typing import Optional

import httpx

from hermes_api.core.exceptions import WikiSearchException

logger = logging.getLogger(__name__)

MEDIAWIKI_API_URL = "https://en.wikipedia.org/w/api.php"
_USER_AGENT = (
    "hermes-api/1.0 (geospatial news aggregator; "
    "https://github.com/your-org/hermes; contact@hermes.example.com)"
)
_MAX_TITLES_PER_REQUEST = 50
_REQUEST_TIMEOUT = 15.0

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}







def _sort_timeline_titles(titles: list[str]) -> list[str]:
    def sort_key(title: str) -> tuple:
        year_match = re.search(r"\b(19|20)\d{2}\b", title)
        year = int(year_match.group(0)) if year_match else 0

        month = 0
        for m_name, m_val in _MONTHS.items():
            if m_name in title.lower():
                month = m_val
                break

        phase_match = re.search(r"\bphase\s+(\d+)\b", title.lower())
        phase = int(phase_match.group(1)) if phase_match else 0

        return (year, month, phase, title)

    return sorted(titles, key=sort_key)




async def search_timeline_titles(query: str, *, limit: int = 50) -> list[str]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f'intitle:"{query}"',
        "srlimit": min(limit, _MAX_TITLES_PER_REQUEST),
        "srnamespace": "0",
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
        logger.info("wikipedia search '%s' returned %s title(s).", query, len(titles))
        return titles
    except httpx.HTTPError:
        logger.exception("http error while searching wikipedia for '%s'.", query)
        return []
    except (KeyError, ValueError):
        logger.exception("failed to parse wikipedia search response for '%s'.", query)
        return []




async def search_wikipedia(query: str, *, limit: int = 5) -> list[str]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": min(limit, _MAX_TITLES_PER_REQUEST),
        "srnamespace": "0",  
        "format": "json",
        "formatversion": "2",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                MEDIAWIKI_API_URL,
                params=params,
                headers={ "User-Agent": _USER_AGENT },
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()

        data = response.json()
        results: list[dict] = data.get("query", {}).get("search", [])
        titles = [r["title"] for r in results if "title" in r]
        logger.info("wikipedia general search '%s' returned %s title(s).", query, len(titles))
        return titles
    except httpx.HTTPError as e:
        logger.exception("http error while searching wikipedia for '%s'.", query)
        raise WikiSearchException(query=query) from e
    except (KeyError, ValueError) as e:
        logger.exception("failed to parse wikipedia search response for '%s'.", query)
        raise WikiSearchException(query=query) from e




async def _fetch_extracts_batch(titles: list[str]) -> dict[str, Optional[str]]:
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
        normalised: dict[str, str] = {t.lower().replace("_", " "): t for t in titles}
        for page in pages:
            if page.get("missing") or page.get("id", 0) == -1:
                continue

            returned_title: str = page.get("title", "")
            extract: str = page.get("extract", "").strip()
            if not extract:
                logger.debug("wikipedia page '%s' returned an empty extract.", returned_title)
                continue
            lookup = returned_title.lower().replace("_", " ")
            caller_key = normalised.get(lookup, returned_title)
            out[caller_key] = extract
    except httpx.HTTPError:
        logger.exception("http error fetching extracts for batch: %s...", titles[:3])
    except (KeyError, ValueError):
        logger.exception("failed to parse extracts response for batch: %s...", titles[:3])

    return out




async def fetch_page_extracts(titles: list[str]) -> dict[str, Optional[str]]:
    if not titles:
        return {}

    seen: set[str] = set()
    unique_titles: list[str] = []
    for t in titles:
        if t not in seen:
            seen.add(t)
            unique_titles.append(t)

    results: dict[str, Optional[str]] = {t: None for t in unique_titles}
    batches = [
        unique_titles[i : i + _MAX_TITLES_PER_REQUEST]
        for i in range(0, len(unique_titles), _MAX_TITLES_PER_REQUEST)
    ]

    for batch in batches:
        batch_result = await _fetch_extracts_batch(batch)
        results.update(batch_result)

    non_null = sum(1 for v in results.values() if v is not None)
    logger.info("fetched extracts for %s/%s wikipedia page(s).", non_null, len(unique_titles))
    return results




async def enumerate_tl_pages(main_title: str) -> list[str]:
    extracts = await fetch_page_extracts([main_title])
    extract = extracts.get(main_title)

    if not extract:
        return []

    search_results = await search_timeline_titles(main_title)

    def _norm(s: str) -> str:
        return s.lower().replace("–", "-").replace("—", "-")

    norm_main = _norm(main_title)
    sub_pages = [
        t for t in search_results if t != main_title and _norm(t).startswith(norm_main)
    ]

    if not sub_pages:
        return [main_title]

    # Check if the main page is an index
    lines = [line.strip() for line in extract.splitlines() if line.strip()]
    is_index = False

    for i in range(len(lines) - 1):
        if lines[i].startswith("==") and lines[i].endswith("=="):
            next_line = lines[i + 1].lower()
            if (
                (next_line.startswith("==") and next_line.endswith("=="))
                or next_line.startswith("see also:")
                or next_line.startswith("main article:")
                or next_line.startswith("further information:")
            ):
                is_index = True
                break

    return _sort_timeline_titles(sub_pages) if is_index else [main_title]

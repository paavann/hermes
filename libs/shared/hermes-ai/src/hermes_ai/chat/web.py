from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlparse

from langchain_tavily import TavilySearch

from hermes_ai.chat.models import WebResult
from hermes_ai.core.config import AiConfig
from hermes_ai.utils.sanitization import sanitize_query_text, strip_html_text


logger = logging.getLogger(__name__)

MAX_RESULTS = 5
MAX_TITLE_CHARS = 300
MAX_SNIPPET_CHARS = 1200
MAX_WEB_QUERY_CHARS = 400


class TavilyTool(Protocol):
    async def ainvoke(self, input: dict[str, object]) -> object: ...


@dataclass(frozen=True, slots=True)
class WebSearchOutcome:
    results: list[WebResult] = field(default_factory=list)
    degraded: bool = False
    failure: str | None = None


def sanitize_text(value: str, limit: int) -> str:
    """Strip HTML markup, invisible controls, and normalize text within ``limit``."""
    return strip_html_text(value, limit=limit)


def validated_url(value: str) -> str | None:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed.geturl()


def source_name_from_url(url: str) -> str | None:
    host = urlparse(url).netloc.lower()
    if not host:
        return None
    return host.removeprefix("www.")


def parse_published_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    elif isinstance(value, int | float):
        return float(value)
    elif isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    else:
        return None


class WebSearchService:
    def __init__(
        self,
        config: AiConfig,
        *,
        tool: TavilyTool | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else config.web_timeout_seconds
        )
        if tool is not None:
            self._tool = tool
        elif config.tavily_api_key:
            self._tool = TavilySearch(
                tavily_api_key=config.tavily_api_key,
                max_results=MAX_RESULTS,
                topic="news",
                search_depth="basic",
                include_answer=False,
                include_raw_content=False,
                handle_tool_error=False,
            )
        else:
            self._tool = None

    @property
    def configured(self) -> bool:
        return self._tool is not None

    def _parse_results(self, raw: object, *, retrieved_at: datetime) -> list[WebResult]:
        if not isinstance(raw, dict):
            return []
        rows = raw.get("results")
        if not isinstance(rows, list):
            return []

        results: list[WebResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = validated_url(str(row.get("url", "")))
            if url is None:
                continue
            title = sanitize_text(str(row.get("title", "")), limit=MAX_TITLE_CHARS)
            if not title:
                continue
            results.append(
                WebResult(
                    title=title,
                    url=url,
                    source_name=source_name_from_url(url),
                    published_at=parse_published_at(row.get("published_date")),
                    retrieved_at=retrieved_at,
                    snippet=sanitize_text(
                        str(row.get("content", "")), limit=MAX_SNIPPET_CHARS
                    ),
                    score=_as_float(row.get("score")),
                )
            )
        results.sort(
            key=lambda result: result.score if result.score is not None else 0.0,
            reverse=True,
        )
        return results[:MAX_RESULTS]

    async def search(
        self,
        query: str,
        *,
        recency_intent: bool = False,
        now: datetime | None = None,
    ) -> WebSearchOutcome:
        if self._tool is None:
            return WebSearchOutcome(degraded=True, failure="tavily is not configured.")

        query = sanitize_query_text(query, limit=MAX_WEB_QUERY_CHARS)
        if not query:
            return WebSearchOutcome(degraded=True, failure="web query is empty.")
        retrieved_at = now or datetime.now(UTC)
        payload: dict[str, object] = {"query": query}
        if recency_intent:
            payload["time_range"] = "week"
        try:
            async with asyncio.timeout(self._timeout_seconds):
                raw = await self._tool.ainvoke(payload)
        except Exception as exc:
            logger.warning("tavily web search failed: %s.", exc)
            return WebSearchOutcome(degraded=True, failure=str(exc))

        results = self._parse_results(raw, retrieved_at=retrieved_at)
        return WebSearchOutcome(results=results)


__all__ = [
    "TavilyTool",
    "WebSearchOutcome",
    "WebSearchService",
    "parse_published_at",
    "sanitize_text",
    "source_name_from_url",
    "validated_url",
]

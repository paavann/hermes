"""Manual source audit.

The audit fetches each configured feed and one sample article so a human can
confirm that a source still publishes a usable feed and decide whether the
source should be ``FULL_TEXT`` or ``SUMMARY_ONLY``. It never touches the
database and never writes the source config.
"""

from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass
from typing import Final, Literal
from urllib.parse import urljoin
import feedparser
import httpx
from hermes_db.services.source import SourceConfigEntry


logger = logging.getLogger(__name__)

BodyVerdict = Literal["open", "blocked", "unknown"]

MAX_BODY_BYTES: Final[int] = 400_000
MAX_SAMPLE_URLS: Final[int] = 3
MAX_ERROR_CHARS: Final[int] = 160

PAYWALL_MARKERS: Final[tuple[str, ...]] = (
    '"isaccessibleforfree": false',
    '"isaccessibleforfree":false',
    'content="article:content_tier" content="locked"',
    'article:content_tier" content="locked',
    'class="paywall',
    'id="paywall',
    "data-paywall",
)


@dataclass(frozen=True, slots=True)
class FeedProbe:
    url: str
    status: int | None
    final_url: str | None
    entries: int
    with_content: int
    sample_urls: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class BodyProbe:
    url: str | None
    verdict: BodyVerdict
    reason: str


@dataclass(frozen=True, slots=True)
class SourceAudit:
    slug: str
    name: str
    provider: str
    policy: str
    primary: FeedProbe
    fallback: FeedProbe | None
    body: BodyProbe


def _bounded_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:MAX_ERROR_CHARS]


def detect_paywall(html: str) -> str | None:
    """Return the matching paywall marker, or None when the page is open."""
    lowered = html.lower()
    for marker in PAYWALL_MARKERS:
        if marker in lowered:
            return marker
    return None


async def probe_feed(client: httpx.AsyncClient, url: str) -> FeedProbe:
    try:
        res = await client.get(url)
    except Exception as exc:
        return FeedProbe(
            url=url,
            status=None,
            final_url=None,
            entries=0,
            with_content=0,
            sample_urls=(),
            error=_bounded_error(exc),
        )

    final_url = str(res.url)
    feed = feedparser.parse(res.text)
    entries = feed.entries
    with_content = sum(
        1 for entry in entries if entry.get("content") or entry.get("content_encoded")
    )
    samples = tuple(
        urljoin(final_url, str(entry.get("link")).strip())
        for entry in entries[:MAX_SAMPLE_URLS]
        if entry.get("link")
    )
    return FeedProbe(
        url=url,
        status=res.status_code,
        final_url=final_url,
        entries=len(entries),
        with_content=with_content,
        sample_urls=samples,
    )


async def probe_body(client: httpx.AsyncClient, url: str) -> BodyProbe:
    try:
        res = await client.get(url)
    except Exception as exc:
        return BodyProbe(url=url, verdict="unknown", reason=_bounded_error(exc))

    if res.status_code in (401, 402, 403):
        return BodyProbe(url=url, verdict="blocked", reason=f"http-{res.status_code}")
    if res.status_code >= 400:
        return BodyProbe(url=url, verdict="unknown", reason=f"http-{res.status_code}")

    html = res.content[:MAX_BODY_BYTES].decode(res.encoding or "utf-8", "replace")
    marker = detect_paywall(html)
    if marker is not None:
        return BodyProbe(url=url, verdict="blocked", reason="paywall-marker")
    return BodyProbe(url=url, verdict="open", reason=f"http-{res.status_code}")


async def audit_source(
    client: httpx.AsyncClient,
    entry: SourceConfigEntry,
) -> SourceAudit:
    slug = entry.get("slug", "unknown")
    primary_url = str(entry.get("feed_url") or "")
    fallback_url = entry.get("fallback_feed_url")

    primary = (
        await probe_feed(client, primary_url)
        if primary_url
        else FeedProbe(
            url="",
            status=None,
            final_url=None,
            entries=0,
            with_content=0,
            sample_urls=(),
            error="missing feed_url",
        )
    )
    fallback = await probe_feed(client, str(fallback_url)) if fallback_url else None

    sample = primary.sample_urls[0] if primary.sample_urls else None
    if sample is None and fallback is not None and fallback.sample_urls:
        sample = fallback.sample_urls[0]
    body = (
        await probe_body(client, sample)
        if sample is not None
        else BodyProbe(url=None, verdict="unknown", reason="no-sample-url")
    )

    return SourceAudit(
        slug=slug,
        name=entry.get("name", slug),
        provider=entry.get("feed_provider", "PUBLISHER"),
        policy=entry.get("fetch_policy", "FULL_TEXT"),
        primary=primary,
        fallback=fallback,
        body=body,
    )


async def audit_sources(
    entries: list[SourceConfigEntry],
    *,
    user_agent: str,
    concurrency: int = 5,
) -> list[SourceAudit]:
    semaphore = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": user_agent}
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers=headers,
    ) as client:

        async def run(entry: SourceConfigEntry) -> SourceAudit:
            async with semaphore:
                try:
                    return await audit_source(client, entry)
                except Exception as exc:
                    logger.warning(
                        "audit failed for source '%s': %s.",
                        entry.get("slug", "unknown"),
                        exc,
                    )
                    raise

        audits = await asyncio.gather(*(run(entry) for entry in entries))

    return sorted(audits, key=lambda audit: audit.slug)


def _feed_cell(probe: FeedProbe | None) -> str:
    if probe is None:
        return "-"
    if probe.status is None:
        return "ERR"
    content = (
        f"{(probe.with_content * 100) // probe.entries}%" if probe.entries else "-"
    )
    return f"{probe.status}/{probe.entries}/{content}"


def format_audit(audits: list[SourceAudit]) -> list[str]:
    """Render one stable report line per source."""
    lines = [
        "slug | primary status/entries/content | fallback status/entries/content "
        "| body verdict | configured provider/policy"
    ]
    for audit in audits:
        line = (
            f"{audit.slug} | {_feed_cell(audit.primary)} "
            f"| {_feed_cell(audit.fallback)} "
            f"| {audit.body.verdict} ({audit.body.reason}) "
            f"| {audit.provider}/{audit.policy}"
        )
        if audit.body.verdict == "blocked" and audit.policy == "FULL_TEXT":
            line += " | MISMATCH: body blocked but policy is FULL_TEXT"
        lines.append(line)
    return lines

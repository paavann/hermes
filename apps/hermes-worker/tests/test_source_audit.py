import asyncio
import httpx
from hermes_worker.services.source_audit import (
    BodyProbe,
    FeedProbe,
    SourceAudit,
    audit_source,
    detect_paywall,
    format_audit,
    probe_body,
    probe_feed,
)


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example World</title>
    <link>https://example.com</link>
    <item>
      <title>First story</title>
      <link>/world/first</link>
      <description>First summary</description>
      <content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/">
        Full first body
      </content:encoded>
    </item>
    <item>
      <title>Second story</title>
      <link>https://example.com/world/second</link>
      <description>Second summary</description>
    </item>
  </channel>
</rss>
"""


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=handler,
        follow_redirects=True,
        timeout=5.0,
    )


def test_detect_paywall_markers() -> None:
    assert detect_paywall('var data = {"isAccessibleForFree": false};') is not None
    assert (
        detect_paywall('<meta property="article:content_tier" content="locked">')
        is not None
    )
    assert detect_paywall('<div class="paywall">Subscribe</div>') is not None
    assert detect_paywall("<article>Open story</article>") is None


def test_probe_feed_counts_entries_and_content() -> None:
    async def _test() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/rss"
            return httpx.Response(200, text=RSS_XML)

        async with _client(httpx.MockTransport(handler)) as client:
            probe = await probe_feed(client, "https://example.com/rss")

        assert probe.status == 200
        assert probe.entries == 2
        assert probe.with_content == 1
        assert probe.sample_urls == (
            "https://example.com/world/first",
            "https://example.com/world/second",
        )
        assert probe.error is None

    asyncio.run(_test())


def test_probe_feed_reports_transport_error() -> None:
    async def _test() -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("unreachable")

        async with _client(httpx.MockTransport(handler)) as client:
            probe = await probe_feed(client, "https://example.com/rss")

        assert probe.status is None
        assert probe.entries == 0
        assert probe.error is not None
        assert "ConnectError" in probe.error

    asyncio.run(_test())


def test_probe_body_detects_paywall() -> None:
    async def _test() -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text='<html><script>{"isAccessibleForFree": false}</script></html>',
            )

        async with _client(httpx.MockTransport(handler)) as client:
            probe = await probe_body(client, "https://example.com/story")

        assert probe.verdict == "blocked"
        assert probe.reason == "paywall-marker"

    asyncio.run(_test())


def test_probe_body_flags_http_blocks() -> None:
    async def _test() -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="Forbidden")

        async with _client(httpx.MockTransport(handler)) as client:
            probe = await probe_body(client, "https://example.com/story")

        assert probe.verdict == "blocked"
        assert probe.reason == "http-403"

    asyncio.run(_test())


def test_probe_body_marks_open_pages() -> None:
    async def _test() -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<article>Open story</article>")

        async with _client(httpx.MockTransport(handler)) as client:
            probe = await probe_body(client, "https://example.com/story")

        assert probe.verdict == "open"
        assert probe.reason == "http-200"

    asyncio.run(_test())


def test_audit_source_falls_back_to_fallback_sample() -> None:
    async def _test() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/primary":
                return httpx.Response(200, text=RSS_XML)
            return httpx.Response(200, text="<article>Open</article>")

        async with _client(httpx.MockTransport(handler)) as client:
            audit = await audit_source(
                client,
                {
                    "slug": "example",
                    "name": "Example",
                    "feed_url": "https://example.com/primary",
                    "feed_provider": "PUBLISHER",
                    "fetch_policy": "FULL_TEXT",
                },
            )

        assert audit.slug == "example"
        assert audit.primary.entries == 2
        assert audit.fallback is None
        assert audit.body.verdict == "open"

    asyncio.run(_test())


def test_audit_source_without_sample_url_reports_unknown() -> None:
    async def _test() -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<rss><channel></channel></rss>")

        async with _client(httpx.MockTransport(handler)) as client:
            audit = await audit_source(
                client,
                {
                    "slug": "empty",
                    "feed_url": "https://example.com/empty",
                },
            )

        assert audit.body.verdict == "unknown"
        assert audit.body.reason == "no-sample-url"

    asyncio.run(_test())


def test_format_audit_flags_policy_mismatch() -> None:
    audit = SourceAudit(
        slug="paywalled",
        name="Paywalled",
        provider="PUBLISHER",
        policy="FULL_TEXT",
        primary=FeedProbe(
            url="https://example.com/rss",
            status=200,
            final_url="https://example.com/rss",
            entries=10,
            with_content=0,
            sample_urls=("https://example.com/story",),
        ),
        fallback=None,
        body=BodyProbe(
            url="https://example.com/story",
            verdict="blocked",
            reason="paywall-marker",
        ),
    )

    lines = format_audit([audit])

    assert "paywalled | 200/10/0% | - | blocked (paywall-marker)" in lines[1]
    assert "MISMATCH" in lines[1]


def test_format_audit_reports_feed_errors() -> None:
    audit = SourceAudit(
        slug="broken",
        name="Broken",
        provider="GOOGLE_NEWS",
        policy="SUMMARY_ONLY",
        primary=FeedProbe(
            url="https://example.com/rss",
            status=None,
            final_url=None,
            entries=0,
            with_content=0,
            sample_urls=(),
            error="ConnectError: unreachable",
        ),
        fallback=None,
        body=BodyProbe(url=None, verdict="unknown", reason="no-sample-url"),
    )

    lines = format_audit([audit])

    assert "broken | ERR | - | unknown (no-sample-url)" in lines[1]
    assert "MISMATCH" not in lines[1]

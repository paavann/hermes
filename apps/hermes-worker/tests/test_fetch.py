import asyncio
import ipaddress
from collections.abc import Sequence
import httpx
from hermes_worker.jobs.fetch import (
    BodyFetcher,
    FetchReason,
    IpAddress,
    is_public_ip,
)


ARTICLE_TEXT = (
    "Rescue teams searched the collapsed buildings on Tuesday after a "
    "magnitude 6.1 earthquake struck the region, officials said, as "
    "neighbours dug through rubble with their hands. At least twelve people "
    "were killed and dozens more were injured, according to the emergency "
    "service. The tremor was centred forty kilometres east of the city and "
    "was felt across the province."
)

ARTICLE_HTML = f"""<!doctype html>
<html><head><title>Quake</title></head>
<body><article><h1>Quake</h1><p>{ARTICLE_TEXT}</p></article></body></html>
"""


async def public_resolver(host: str, port: int) -> Sequence[IpAddress]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        return [ipaddress.ip_address("93.184.216.34")]


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler, timeout=5.0)


def _fetcher(client: httpx.AsyncClient, *, min_body_chars: int = 300) -> BodyFetcher:
    return BodyFetcher(
        user_agent="hermes-test/1.0",
        client=client,
        resolver=public_resolver,
        min_body_chars=min_body_chars,
        connect_timeout=1.0,
        read_timeout=1.0,
    )


def test_is_public_ip_rejects_non_global_ranges() -> None:
    assert is_public_ip(ipaddress.ip_address("93.184.216.34")) is True
    assert is_public_ip(ipaddress.ip_address("8.8.8.8")) is True
    assert is_public_ip(ipaddress.ip_address("127.0.0.1")) is False
    assert is_public_ip(ipaddress.ip_address("10.1.2.3")) is False
    assert is_public_ip(ipaddress.ip_address("169.254.169.254")) is False
    assert is_public_ip(ipaddress.ip_address("::1")) is False
    assert is_public_ip(ipaddress.ip_address("::ffff:127.0.0.1")) is False


def test_fetch_success_extracts_main_content() -> None:
    async def _test() -> None:
        paths: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            paths.append(request.url.path)
            if request.url.path == "/robots.txt":
                return httpx.Response(404)
            return httpx.Response(
                200,
                text=ARTICLE_HTML,
                headers={"content-type": "text/html; charset=utf-8"},
            )

        async with _client(httpx.MockTransport(handler)) as client:
            result = await _fetcher(client).fetch("https://news.example.com/story")

        assert result.ok is True
        assert result.http_status == 200
        assert result.text is not None
        assert "magnitude 6.1 earthquake" in result.text
        assert paths == ["/robots.txt", "/story"]

    asyncio.run(_test())


def test_fetch_detects_paywall_marker() -> None:
    async def _test() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/robots.txt":
                return httpx.Response(404)
            return httpx.Response(
                200,
                text=ARTICLE_HTML.replace("<h1>Quake</h1>", '<div class="paywall">Subscribe</div>'),
                headers={"content-type": "text/html; charset=utf-8"},
            )

        async with _client(httpx.MockTransport(handler)) as client:
            result = await _fetcher(client).fetch("https://news.example.com/story")

        assert result.reason == FetchReason.PAYWALL
        assert result.text is None
        assert result.http_status == 200

    asyncio.run(_test())


def test_fetch_reports_short_body() -> None:
    async def _test() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/robots.txt":
                return httpx.Response(404)
            return httpx.Response(
                200,
                text="<html><body><article><p>Too short.</p></article></body></html>",
                headers={"content-type": "text/html"},
            )

        async with _client(httpx.MockTransport(handler)) as client:
            result = await _fetcher(client).fetch("https://news.example.com/story")

        assert result.reason == FetchReason.SHORT
        assert result.text is None

    asyncio.run(_test())


def test_fetch_reports_http_error() -> None:
    async def _test() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/robots.txt":
                return httpx.Response(404)
            return httpx.Response(403)

        async with _client(httpx.MockTransport(handler)) as client:
            result = await _fetcher(client).fetch("https://news.example.com/story")

        assert result.reason == FetchReason.HTTP_ERROR
        assert result.http_status == 403

    asyncio.run(_test())


def test_fetch_blocks_private_resolution_before_request() -> None:
    async def _test() -> None:
        paths: list[str] = []

        async def private_resolver(host: str, port: int) -> Sequence[IpAddress]:
            return [ipaddress.ip_address("127.0.0.1")]

        def handler(request: httpx.Request) -> httpx.Response:
            paths.append(request.url.path)
            return httpx.Response(200, text=ARTICLE_HTML)

        async with _client(httpx.MockTransport(handler)) as client:
            fetcher = BodyFetcher(
                user_agent="hermes-test/1.0",
                client=client,
                resolver=private_resolver,
            )
            result = await fetcher.fetch("https://internal.example.com/story")

        assert result.reason == FetchReason.BLOCKED_TARGET
        assert paths == []

    asyncio.run(_test())


def test_fetch_respects_robots_disallow() -> None:
    async def _test() -> None:
        paths: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            paths.append(request.url.path)
            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nDisallow: /private\n",
                )
            return httpx.Response(200, text=ARTICLE_HTML)

        async with _client(httpx.MockTransport(handler)) as client:
            result = await _fetcher(client).fetch(
                "https://news.example.com/private/story"
            )

        assert result.reason == FetchReason.ROBOTS_DISALLOWED
        assert paths == ["/robots.txt"]

    asyncio.run(_test())


def test_fetch_blocks_redirect_to_private_host() -> None:
    async def _test() -> None:
        paths: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            paths.append(request.url.path)
            if request.url.path == "/robots.txt":
                return httpx.Response(404)
            if request.url.path == "/start":
                return httpx.Response(
                    302,
                    headers={"location": "http://127.0.0.1/secret"},
                )
            return httpx.Response(200, text=ARTICLE_HTML)

        async with _client(httpx.MockTransport(handler)) as client:
            result = await _fetcher(client).fetch("https://news.example.com/start")

        assert result.reason == FetchReason.BLOCKED_TARGET
        assert paths == ["/robots.txt", "/start"]

    asyncio.run(_test())


def test_fetch_rejects_non_http_scheme() -> None:
    async def _test() -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise AssertionError("no request should be made")

        async with _client(httpx.MockTransport(handler)) as client:
            result = await _fetcher(client).fetch("file:///etc/passwd")

        assert result.reason == FetchReason.INVALID_URL

    asyncio.run(_test())


def test_fetch_rejects_credentials_and_unusual_ports() -> None:
    async def _test() -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise AssertionError("no request should be made")

        async with _client(httpx.MockTransport(handler)) as client:
            credentials = await _fetcher(client).fetch(
                "https://user:pass@news.example.com/story"
            )
            port = await _fetcher(client).fetch(
                "https://news.example.com:8443/story"
            )

        assert credentials.reason == FetchReason.INVALID_URL
        assert port.reason == FetchReason.INVALID_URL

    asyncio.run(_test())

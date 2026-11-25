from __future__ import annotations
import asyncio
import base64
import enum
import html as html_lib
import ipaddress
import json
import logging
import re
import socket
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from urllib.parse import SplitResult, urljoin, urlsplit
import httpx
import trafilatura
from hermes_worker.jobs.robots import RobotsCache
from hermes_worker.jobs.urls import GOOGLE_NEWS_HOST
from hermes_worker.services.source_audit import detect_paywall


logger = logging.getLogger(__name__)

IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
Resolver = Callable[[str, int], Awaitable[Sequence[IpAddress]]]

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
ALLOWED_PORTS = frozenset({80, 443})
MAX_ROBOTS_BYTES = 512_000
MAX_ERROR_CHARS = 160
GOOGLE_NEWS_BATCHEXECUTE_URL = (
    "https://news.google.com/_/DotsSplashUi/data/batchexecute"
)
_GN_TOKEN_RE = re.compile(r"^/(?:rss/)?articles/([^/?#]+)")
_GN_URL_BYTES_RE = re.compile(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")
_GN_ATTR_ID_RE = re.compile(r'data-n-a-id=["\']([^"\']+)["\']')
_GN_ATTR_TS_RE = re.compile(r'data-n-a-ts=["\']([^"\']+)["\']')
_GN_ATTR_SG_RE = re.compile(r'data-n-a-sg=["\']([^"\']+)["\']')


def is_google_news_article_url(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    return host == GOOGLE_NEWS_HOST and bool(_GN_TOKEN_RE.match(parts.path))


def _is_external_http_url(candidate: str) -> bool:
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    if parts.scheme.lower() not in {"http", "https"} or not host:
        return False
    return host != GOOGLE_NEWS_HOST and not host.endswith(".google.com")


def decode_legacy_google_news_url(url: str) -> str | None:
    parts = urlsplit(url)
    if (parts.hostname or "").lower() != GOOGLE_NEWS_HOST:
        return None
    match = _GN_TOKEN_RE.match(parts.path)
    if not match:
        return None
    token = match.group(1)
    if token.startswith("AU_yqL"):
        return None
    try:
        padded = token + ("=" * (-len(token) % 4))
        raw = base64.urlsafe_b64decode(padded)
    except Exception:
        return None
    if b"AU_yqL" in raw:
        return None
    url_match = _GN_URL_BYTES_RE.search(raw)
    if not url_match:
        return None
    candidate = url_match.group(0).decode("ascii", errors="ignore")
    return candidate if _is_external_http_url(candidate) else None


def _parse_google_news_batchexecute_response(payload: str) -> str | None:
    for line in payload.splitlines():
        stripped = line.strip()
        if not stripped.startswith("["):
            continue
        try:
            outer = json.loads(stripped)
        except ValueError:
            continue
        if not isinstance(outer, list):
            continue
        for entry in outer:
            if not (isinstance(entry, list) and len(entry) >= 3):
                continue
            if entry[0] != "wrb.fr" or entry[1] != "Fbv4je":
                continue
            inner_raw = entry[2]
            if not isinstance(inner_raw, str):
                continue
            try:
                inner = json.loads(inner_raw)
            except ValueError:
                continue
            if (
                isinstance(inner, list)
                and len(inner) >= 2
                and inner[0] == "garturlres"
                and isinstance(inner[1], str)
                and _is_external_http_url(inner[1])
            ):
                return inner[1]
    return None


class FetchReason(enum.StrEnum):
    OK = "ok"
    SHORT = "short"
    PAYWALL = "paywall"
    HTTP_ERROR = "http_error"
    ROBOTS_DISALLOWED = "robots_disallowed"
    BLOCKED_TARGET = "blocked_target"
    INVALID_URL = "invalid_url"
    TOO_LARGE = "too_large"
    TOO_MANY_REDIRECTS = "too_many_redirects"
    UNSUPPORTED_CONTENT = "unsupported_content"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    reason: FetchReason
    text: str | None = None
    http_status: int | None = None
    detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.reason == FetchReason.OK


class _BlockedTargetError(Exception):
    def __init__(self, reason: FetchReason, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def is_public_ip(address: IpAddress) -> bool:
    """Reject loopback, private, link-local, reserved, and multicast targets."""
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_global and not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def _resolve_sync(host: str, port: int) -> list[IpAddress]:
    addresses: list[IpAddress] = []
    for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        addresses.append(ipaddress.ip_address(info[4][0]))
    return addresses


async def _default_resolver(host: str, port: int) -> list[IpAddress]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _resolve_sync, host, port)


@dataclass(frozen=True, slots=True)
class _Hop:
    result: FetchResult | None = None
    redirect: str | None = None


class BodyFetcher:
    """Transient article body fetcher with SSRF and robots protection.

    The body is returned to the caller and never persisted. Requests validate
    every redirect hop, cap the response size, and cache robots.txt per host
    for the lifetime of one stage run.
    """

    def __init__(
        self,
        *,
        user_agent: str,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
        max_bytes: int = 2_000_000,
        max_redirects: int = 5,
        per_host_concurrency: int = 2,
        min_body_chars: int = 300,
        client: httpx.AsyncClient | None = None,
        resolver: Resolver | None = None,
    ) -> None:
        self._user_agent = user_agent
        self._max_bytes = max_bytes
        self._max_redirects = max_redirects
        self._per_host_concurrency = per_host_concurrency
        self._min_body_chars = min_body_chars
        self._resolver = resolver or _default_resolver
        self._robots = RobotsCache(user_agent=user_agent)
        self._host_semaphores: dict[str, asyncio.Semaphore] = {}
        self._owned_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=read_timeout,
                pool=read_timeout,
            ),
            follow_redirects=False,
        )

    async def __aenter__(self) -> BodyFetcher:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owned_client:
            await self._client.aclose()

    def _host_semaphore(self, host: str) -> asyncio.Semaphore:
        semaphore = self._host_semaphores.get(host)
        if semaphore is None:
            semaphore = asyncio.Semaphore(self._per_host_concurrency)
            self._host_semaphores[host] = semaphore
        return semaphore

    async def _validate_target(self, url: str) -> SplitResult:
        try:
            parts = urlsplit(url)
            port = parts.port
        except ValueError as exc:
            raise _BlockedTargetError(FetchReason.INVALID_URL, str(exc)) from exc

        if parts.scheme not in {"http", "https"}:
            raise _BlockedTargetError(FetchReason.INVALID_URL, "scheme")
        if parts.username is not None or parts.password is not None:
            raise _BlockedTargetError(FetchReason.INVALID_URL, "credentials")
        host = parts.hostname
        if not host:
            raise _BlockedTargetError(FetchReason.INVALID_URL, "host")
        if port is not None and port not in ALLOWED_PORTS:
            raise _BlockedTargetError(FetchReason.INVALID_URL, "port")

        resolved_port = port or (443 if parts.scheme == "https" else 80)
        try:
            ascii_host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise _BlockedTargetError(
                FetchReason.INVALID_URL,
                "host-encoding",
            ) from exc

        try:
            addresses = await self._resolver(ascii_host, resolved_port)
        except OSError as exc:
            raise _BlockedTargetError(
                FetchReason.BLOCKED_TARGET,
                f"unresolvable: {exc}",
            ) from exc
        if not addresses:
            raise _BlockedTargetError(FetchReason.BLOCKED_TARGET, "unresolvable")
        if not all(is_public_ip(address) for address in addresses):
            raise _BlockedTargetError(FetchReason.BLOCKED_TARGET, "non-public-ip")
        return parts

    async def fetch(self, url: str) -> FetchResult:
        current = url
        for _ in range(self._max_redirects + 1):
            try:
                parts = await self._validate_target(current)
            except _BlockedTargetError as exc:
                return FetchResult(
                    url=current,
                    reason=exc.reason,
                    detail=exc.detail[:MAX_ERROR_CHARS],
                )

            legacy_target = decode_legacy_google_news_url(current)
            if legacy_target is not None:
                current = legacy_target
                continue

            host = (parts.hostname or "").lower()
            async with self._host_semaphore(host):
                allowed = await self._robots.allowed(current, self._load_robots)
                if not allowed:
                    return FetchResult(
                        url=current,
                        reason=FetchReason.ROBOTS_DISALLOWED,
                        detail="robots.txt",
                    )
                try:
                    hop = await self._request_once(current)
                except Exception as exc:
                    return FetchResult(
                        url=current,
                        reason=FetchReason.ERROR,
                        detail=f"{type(exc).__name__}: {exc}"[:MAX_ERROR_CHARS],
                    )

            if hop.redirect is not None:
                current = urljoin(current, hop.redirect)
                continue
            if hop.result is not None:
                return hop.result
            return FetchResult(
                url=current,
                reason=FetchReason.ERROR,
                detail="empty-hop",
            )

        return FetchResult(
            url=current,
            reason=FetchReason.TOO_MANY_REDIRECTS,
            detail=f"more than {self._max_redirects} redirects",
        )

    async def _resolve_google_news_url(
        self, page_url: str, page_html: str
    ) -> str | None:
        id_match = _GN_ATTR_ID_RE.search(page_html)
        ts_match = _GN_ATTR_TS_RE.search(page_html)
        sg_match = _GN_ATTR_SG_RE.search(page_html)
        path_match = _GN_TOKEN_RE.match(urlsplit(page_url).path)
        fallback_id = path_match.group(1) if path_match else None
        article_id = (
            html_lib.unescape(id_match.group(1)) if id_match else fallback_id
        )
        if not (article_id and ts_match and sg_match):
            return None

        ts_raw = html_lib.unescape(ts_match.group(1))
        sg = html_lib.unescape(sg_match.group(1))
        ts_val: int | str = int(ts_raw) if ts_raw.isdigit() else ts_raw

        try:
            await self._validate_target(GOOGLE_NEWS_BATCHEXECUTE_URL)
        except _BlockedTargetError:
            return None

        rpc_inner = json.dumps(
            [
                "garturlreq",
                [
                    [
                        "X",
                        "X",
                        ["X", "X"],
                        None,
                        None,
                        1,
                        1,
                        "US:en",
                        None,
                        1,
                        None,
                        None,
                        None,
                        None,
                        None,
                        0,
                        1,
                    ],
                    "X",
                    "X",
                    1,
                    [1, 1, 1],
                    1,
                    1,
                    None,
                    0,
                    0,
                    None,
                    0,
                ],
                article_id,
                ts_val,
                sg,
            ],
            separators=(",", ":"),
        )
        f_req = json.dumps(
            [[["Fbv4je", rpc_inner, None, "generic"]]],
            separators=(",", ":"),
        )
        try:
            response = await self._client.post(
                GOOGLE_NEWS_BATCHEXECUTE_URL,
                data={"f.req": f_req},
                headers={
                    "User-Agent": self._user_agent,
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Origin": "https://news.google.com",
                    "Referer": "https://news.google.com/",
                },
                follow_redirects=False,
            )
        except Exception as exc:
            logger.debug("google news resolve failed for %s: %s.", page_url, exc)
            return None
        if response.status_code != 200 or len(response.content) > self._max_bytes:
            return None
        return _parse_google_news_batchexecute_response(response.text)

    async def _request_once(self, url: str) -> _Hop:
        headers = {
            "User-Agent": self._user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en;q=0.8,*;q=0.5",
        }
        async with self._client.stream(
            "GET",
            url,
            headers=headers,
            follow_redirects=False,
        ) as response:
            status = response.status_code
            if status in REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    return _Hop(
                        result=FetchResult(
                            url=url,
                            reason=FetchReason.HTTP_ERROR,
                            http_status=status,
                            detail="redirect-without-location",
                        )
                    )
                return _Hop(redirect=location)

            if status != 200:
                return _Hop(
                    result=FetchResult(
                        url=url,
                        reason=FetchReason.HTTP_ERROR,
                        http_status=status,
                        detail=f"http-{status}",
                    )
                )

            content_type = (response.headers.get("content-type") or "").lower()
            if (
                content_type
                and "html" not in content_type
                and "text/" not in content_type
            ):
                return _Hop(
                    result=FetchResult(
                        url=url,
                        reason=FetchReason.UNSUPPORTED_CONTENT,
                        http_status=status,
                        detail=content_type[:MAX_ERROR_CHARS],
                    )
                )

            body, exceeded = await self._read_limited(response, self._max_bytes)
            if exceeded:
                return _Hop(
                    result=FetchResult(
                        url=url,
                        reason=FetchReason.TOO_LARGE,
                        http_status=status,
                        detail=f"max {self._max_bytes} bytes",
                    )
                )

            html = body.decode(response.encoding or "utf-8", errors="replace")
            if is_google_news_article_url(url):
                resolved_url = await self._resolve_google_news_url(url, html)
                if resolved_url is not None:
                    return _Hop(redirect=resolved_url)
            if detect_paywall(html) is not None:
                return _Hop(
                    result=FetchResult(
                        url=url,
                        reason=FetchReason.PAYWALL,
                        http_status=status,
                        detail="paywall-marker",
                    )
                )

            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                include_links=False,
                favor_precision=True,
            )
            text = " ".join(extracted.split()) if extracted else ""
            if len(text) < self._min_body_chars:
                return _Hop(
                    result=FetchResult(
                        url=url,
                        reason=FetchReason.SHORT,
                        http_status=status,
                        detail=f"{len(text)} chars",
                    )
                )
            return _Hop(
                result=FetchResult(
                    url=url,
                    reason=FetchReason.OK,
                    text=text,
                    http_status=status,
                )
            )

    async def _load_robots(self, origin: str) -> str | None:
        robots_url = f"{origin}/robots.txt"
        try:
            await self._validate_target(robots_url)
        except _BlockedTargetError:
            return None

        try:
            async with self._client.stream(
                "GET",
                robots_url,
                headers={"User-Agent": self._user_agent},
                follow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    return None
                body, _ = await self._read_limited(response, MAX_ROBOTS_BYTES)
                return body.decode("utf-8", errors="replace")
        except Exception as exc:
            logger.debug("robots fetch failed for %s: %s.", origin, exc)
            return None

    @staticmethod
    async def _read_limited(
        response: httpx.Response,
        max_bytes: int,
    ) -> tuple[bytes, bool]:
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            remaining = max_bytes - total
            if len(chunk) > remaining:
                chunks.append(chunk[:remaining])
                return b"".join(chunks), True
            chunks.append(chunk)
            total += len(chunk)
        return b"".join(chunks), False

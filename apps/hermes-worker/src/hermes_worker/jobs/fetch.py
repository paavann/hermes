from __future__ import annotations
import asyncio
import enum
import ipaddress
import logging
import socket
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from urllib.parse import SplitResult, urljoin, urlsplit
import httpx
import trafilatura
from hermes_worker.jobs.robots import RobotsCache
from hermes_worker.services.source_audit import detect_paywall


logger = logging.getLogger(__name__)

IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
Resolver = Callable[[str, int], Awaitable[Sequence[IpAddress]]]

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
ALLOWED_PORTS = frozenset({80, 443})
MAX_ROBOTS_BYTES = 512_000
MAX_ERROR_CHARS = 160


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

    async def _request_once(self, url: str) -> _Hop:
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
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

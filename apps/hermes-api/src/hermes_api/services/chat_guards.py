from __future__ import annotations

import math
import time
import asyncio
import hashlib
import secrets

from collections import deque
from collections.abc import AsyncIterator, Callable

from contextlib import asynccontextmanager

from datetime import UTC, date, datetime, timedelta
from datetime import time as datetime_time

from fastapi import Request

from hermes_api.core.exceptions import (
    ChatBudgetExhausted,
    ChatBusy,
    ChatRateLimitExceeded,
)


RATE_LIMIT_MAX_KEYS = 4096


def hash_client_ip(ip: str, salt: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(salt)
    digest.update(b":")
    digest.update(ip.encode("utf-8"))
    return digest.hexdigest()


def extract_client_ip(
    *,
    client_host: str | None,
    forwarded_for: str | None,
    trust_proxy_headers: bool,
) -> str:
    if trust_proxy_headers and forwarded_for:
        first = forwarded_for.split(",", maxsplit=1)[0].strip()
        if first:
            return first
    return client_host or "unknown"


def estimate_tokens(prompt_chars: int, max_output_tokens: int) -> int:
    prompt_tokens = math.ceil(max(0, prompt_chars) / 4)
    return max(1, prompt_tokens + max(0, max_output_tokens))


class SlidingWindowRateLimiter:
    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive.")
        self._limit = limit
        self._window_seconds = float(window_seconds)
        self._clock = clock
        self._events: dict[str, deque[float]] = {}

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def window_seconds(self) -> float:
        return self._window_seconds

    def check(self, key: str) -> int:
        now = self._clock()
        timestamps = self._events.get(key)
        if timestamps is None:
            timestamps = deque()
            self._events[key] = timestamps
        self._prune(timestamps, now)

        if len(timestamps) >= self._limit:
            oldest = timestamps[0]
            retry_after = max(1, math.ceil(oldest + self._window_seconds - now))
            raise ChatRateLimitExceeded(
                retry_after,
                limit=self._limit,
                remaining=0,
            )

        timestamps.append(now)
        self._prune_stale_keys(now)
        return self._limit - len(timestamps)

    def _prune(self, timestamps: deque[float], now: float) -> None:
        cutoff = now - self._window_seconds
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

    def _prune_stale_keys(self, now: float) -> None:
        if len(self._events) <= RATE_LIMIT_MAX_KEYS:
            return
        cutoff = now - self._window_seconds
        stale = [
            key
            for key, timestamps in self._events.items()
            if not timestamps or timestamps[-1] <= cutoff
        ]
        for key in stale:
            del self._events[key]


class BudgetReservation:
    """A reserved share of the daily token budget for one chat turn."""

    def __init__(self, budget: DailyTokenBudget, tokens: int) -> None:
        self._budget = budget
        self._tokens = tokens
        self._settled = False

    @property
    def tokens(self) -> int:
        return self._tokens

    @property
    def settled(self) -> bool:
        return self._settled

    def reconcile(self, actual_tokens: int) -> None:
        """Replace the estimate with reported usage and release the hold."""
        if self._settled:
            return
        self._settled = True
        self._budget._settle(self._tokens, max(0, int(actual_tokens)))

    def release(self) -> None:
        """Release the hold without recording usage (failure/disconnect)."""
        if self._settled:
            return
        self._settled = True
        self._budget._release(self._tokens)


class DailyTokenBudget:
    """Global daily token budget with reservations and UTC-midnight reset."""

    def __init__(
        self,
        limit: int,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if limit < 0:
            raise ValueError("limit must not be negative.")
        self._limit = limit
        self._clock = clock or _utc_now
        self._day: date = self._today()
        self._used = 0
        self._reserved = 0

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def used(self) -> int:
        self._roll()
        return self._used

    @property
    def reserved(self) -> int:
        self._roll()
        return self._reserved

    @property
    def remaining(self) -> int:
        self._roll()
        return max(0, self._limit - self._used - self._reserved)

    @property
    def disabled(self) -> bool:
        return self._limit == 0

    def reserve(self, estimated_tokens: int) -> BudgetReservation:
        """Reserve an estimate or raise when the remaining budget is short."""
        self._roll()
        estimate = max(1, int(estimated_tokens))
        if self.disabled:
            return BudgetReservation(self, 0)

        if self._used + self._reserved + estimate > self._limit:
            raise ChatBudgetExhausted(
                self._seconds_until_reset(),
                limit=self._limit,
                used=self._used,
                reserved=self._reserved,
            )

        self._reserved += estimate
        return BudgetReservation(self, estimate)

    def _settle(self, reserved: int, actual: int) -> None:
        if self.disabled:
            return
        self._roll()
        self._reserved = max(0, self._reserved - reserved)
        self._used += actual

    def _release(self, reserved: int) -> None:
        if self.disabled:
            return
        self._roll()
        self._reserved = max(0, self._reserved - reserved)

    def _roll(self) -> None:
        today = self._today()
        if today != self._day:
            self._day = today
            self._used = 0
            self._reserved = 0

    def _today(self) -> date:
        now = self._clock()
        if now.tzinfo is None:
            return now.date()
        return now.astimezone(UTC).date()

    def _seconds_until_reset(self) -> int:
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        tomorrow = datetime.combine(
            now.astimezone(UTC).date() + timedelta(days=1),
            datetime_time.min,
            tzinfo=UTC,
        )
        return max(1, math.ceil((tomorrow - now.astimezone(UTC)).total_seconds()))


class ConcurrencyGuard:
    """Bounded concurrent chat streams with a short queue timeout."""

    def __init__(
        self,
        limit: int,
        *,
        queue_timeout_seconds: float = 5.0,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be positive.")
        self._limit = limit
        self._semaphore = asyncio.Semaphore(limit)
        self._queue_timeout_seconds = max(0.0, float(queue_timeout_seconds))

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def available(self) -> int:
        return int(getattr(self._semaphore, "_value", 0))

    @property
    def queue_timeout_seconds(self) -> float:
        return self._queue_timeout_seconds

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """Acquire a stream slot or raise ``ChatBusy`` after the queue wait."""
        await self.acquire()
        try:
            yield
        finally:
            self.release()

    async def acquire(self) -> None:
        """Acquire one stream slot, waiting at most the queue timeout."""
        try:
            if self._queue_timeout_seconds <= 0:
                if self._semaphore.locked():
                    raise ChatBusy()
                await self._semaphore.acquire()
            else:
                async with asyncio.timeout(self._queue_timeout_seconds):
                    await self._semaphore.acquire()
        except TimeoutError:
            raise ChatBusy() from None

    def release(self) -> None:
        self._semaphore.release()


class ChatGuards:
    def __init__(
        self,
        *,
        rate_limit_requests: int,
        rate_limit_window_seconds: float,
        daily_token_budget: int,
        max_concurrent: int,
        queue_timeout_seconds: float,
        trust_proxy_headers: bool,
        salt: bytes | None = None,
        rate_clock: Callable[[], float] = time.monotonic,
        budget_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.rate_limiter = SlidingWindowRateLimiter(
            limit=rate_limit_requests,
            window_seconds=rate_limit_window_seconds,
            clock=rate_clock,
        )
        self.budget = DailyTokenBudget(
            daily_token_budget,
            clock=budget_clock,
        )
        self.concurrency = ConcurrencyGuard(
            max_concurrent,
            queue_timeout_seconds=queue_timeout_seconds,
        )
        self._salt = salt or secrets.token_bytes(32)
        self._trust_proxy_headers = trust_proxy_headers

    @property
    def trust_proxy_headers(self) -> bool:
        return self._trust_proxy_headers

    def client_key(self, request: Request) -> str:
        client = request.client
        ip = extract_client_ip(
            client_host=client.host if client is not None else None,
            forwarded_for=request.headers.get("x-forwarded-for"),
            trust_proxy_headers=self._trust_proxy_headers,
        )
        return hash_client_ip(ip, self._salt)

    def check_rate_limit(self, request: Request) -> str:
        """Apply the per-client rate limit and return the hashed client key."""
        key = self.client_key(request)
        self.rate_limiter.check(key)
        return key


def _utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "BudgetReservation",
    "ChatGuards",
    "ConcurrencyGuard",
    "DailyTokenBudget",
    "SlidingWindowRateLimiter",
    "estimate_tokens",
    "extract_client_ip",
    "hash_client_ip",
]

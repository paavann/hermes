"""Tests for chat rate, budget, and concurrency guards."""

from __future__ import annotations
import asyncio
from datetime import UTC, datetime
import pytest
from starlette.requests import Request
from hermes_api.core.exceptions import (
    ChatBudgetExhausted,
    ChatBusy,
    ChatRateLimitExceeded,
)
from hermes_api.services.chat_guards import (
    ChatGuards,
    ConcurrencyGuard,
    DailyTokenBudget,
    SlidingWindowRateLimiter,
    estimate_tokens,
    extract_client_ip,
    hash_client_ip,
)


SALT = b"0123456789abcdef0123456789abcdef"


class FakeClock:
    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _request(
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    client: tuple[str, int] | None = ("203.0.113.7", 1234),
) -> Request:
    return Request(
        {
            "type": "http",
            "headers": headers or [],
            "client": client,
        }
    )


def test_rate_limiter_rejects_with_retry_after() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60.0, clock=clock)

    assert limiter.check("client-a") == 1
    assert limiter.check("client-a") == 0

    with pytest.raises(ChatRateLimitExceeded) as first:
        limiter.check("client-a")
    assert first.value.status_code == 429
    assert first.value.err_code == "CHAT_RATE_LIMIT_EXCEEDED"
    assert first.value.headers["Retry-After"] == "60"
    assert first.value.headers["X-RateLimit-Limit"] == "2"
    assert first.value.headers["X-RateLimit-Remaining"] == "0"

    clock.advance(30)
    with pytest.raises(ChatRateLimitExceeded) as second:
        limiter.check("client-a")
    assert second.value.headers["Retry-After"] == "30"

    clock.advance(30)
    assert limiter.check("client-a") == 1


def test_rate_limiter_is_per_key() -> None:
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60.0, clock=FakeClock())

    limiter.check("client-a")
    assert limiter.check("client-b") == 0


def test_budget_rejects_and_resets_at_utc_midnight() -> None:
    now = [datetime(2026, 11, 7, 23, 59, 0, tzinfo=UTC)]
    budget = DailyTokenBudget(100, clock=lambda: now[0])

    first = budget.reserve(60)
    assert first.tokens == 60
    assert budget.reserved == 60
    assert budget.remaining == 40

    with pytest.raises(ChatBudgetExhausted) as exhausted:
        budget.reserve(50)
    assert exhausted.value.status_code == 429
    assert exhausted.value.err_code == "CHAT_BUDGET_EXHAUSTED"
    assert exhausted.value.headers["Retry-After"] == "60"
    assert exhausted.value.details["used"] == 0
    assert exhausted.value.details["reserved"] == 60

    first.release()
    now[0] = datetime(2026, 11, 8, 0, 0, 0, tzinfo=UTC)
    assert budget.used == 0
    assert budget.reserved == 0
    second = budget.reserve(100)
    assert second.tokens == 100
    second.release()


def test_budget_reservation_release_frees_the_estimate() -> None:
    budget = DailyTokenBudget(100, clock=lambda: datetime.now(UTC))

    reservation = budget.reserve(60)
    assert budget.remaining == 40
    reservation.release()

    assert budget.reserved == 0
    assert budget.used == 0
    assert budget.reserve(100).tokens == 100


def test_budget_reconciliation_records_actual_usage_once() -> None:
    budget = DailyTokenBudget(100, clock=lambda: datetime.now(UTC))

    reservation = budget.reserve(60)
    reservation.reconcile(25)

    assert budget.used == 25
    assert budget.reserved == 0

    reservation.release()
    reservation.reconcile(90)
    assert budget.used == 25


def test_budget_zero_disables_accounting() -> None:
    budget = DailyTokenBudget(0, clock=lambda: datetime.now(UTC))

    reservation = budget.reserve(10_000_000)
    assert reservation.tokens == 0
    reservation.reconcile(500)
    reservation.release()

    assert budget.used == 0
    assert budget.reserved == 0
    assert budget.disabled is True


def test_client_ip_hash_is_salted_and_stable() -> None:
    first = hash_client_ip("203.0.113.7", SALT)

    assert first == hash_client_ip("203.0.113.7", SALT)
    assert first != hash_client_ip("203.0.113.7", b"different-salt-value")
    assert first != "203.0.113.7"
    assert len(first) == 64


def test_extract_client_ip_honors_proxy_trust() -> None:
    forwarded = "203.0.113.9, 10.0.0.1"

    assert (
        extract_client_ip(
            client_host="10.0.0.1",
            forwarded_for=forwarded,
            trust_proxy_headers=False,
        )
        == "10.0.0.1"
    )
    assert (
        extract_client_ip(
            client_host="10.0.0.1",
            forwarded_for=forwarded,
            trust_proxy_headers=True,
        )
        == "203.0.113.9"
    )


def _guards(*, trust_proxy_headers: bool = False) -> ChatGuards:
    return ChatGuards(
        rate_limit_requests=10,
        rate_limit_window_seconds=60.0,
        daily_token_budget=1000,
        max_concurrent=2,
        queue_timeout_seconds=0.5,
        trust_proxy_headers=trust_proxy_headers,
        salt=SALT,
    )


def test_chat_guards_hash_client_key_and_rate_limit() -> None:
    guards = _guards()
    request = _request()

    key = guards.check_rate_limit(request)

    assert key == hash_client_ip("203.0.113.7", SALT)
    assert "203.0.113.7" not in key


def test_chat_guards_uses_forwarded_header_only_when_trusted() -> None:
    forwarded = _request(headers=[(b"x-forwarded-for", b"198.51.100.4")])

    trusted = _guards(trust_proxy_headers=True).client_key(forwarded)
    untrusted = _guards(trust_proxy_headers=False).client_key(forwarded)

    assert trusted == hash_client_ip("198.51.100.4", SALT)
    assert untrusted == hash_client_ip("203.0.113.7", SALT)


def test_concurrency_guard_times_out_and_releases_slots() -> None:
    async def run() -> None:
        guard = ConcurrencyGuard(1, queue_timeout_seconds=0.01)
        async with guard.slot():
            with pytest.raises(ChatBusy) as busy:
                async with guard.slot():
                    pass
            assert busy.value.status_code == 503
            assert busy.value.headers["Retry-After"] == "1"

        async with guard.slot():
            pass

    asyncio.run(run())


def test_estimate_tokens_includes_output_budget() -> None:
    assert estimate_tokens(400, 1200) == 1300
    assert estimate_tokens(0, 0) == 1

"""Unit tests for the worker job budget and stage runner."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
import pytest
from hermes_worker.jobs.context import (
    JobContext,
    LlmBudget,
    StageName,
    StageOutcome,
    StageStats,
    WorkerIdentity,
)
from hermes_worker.jobs.errors import BudgetExhaustedError
from hermes_worker.jobs.locks import LockName
from hermes_worker.jobs.runner import format_error, run_stages


def test_budget_reserves_and_reports_remaining() -> None:
    budget = LlmBudget(max_llm_calls=5)

    budget.reserve_llm_calls()
    budget.reserve_llm_calls(2)

    assert budget.used_llm_calls == 3
    assert budget.remaining_llm_calls == 2


def test_budget_rejects_exhausted_reservation() -> None:
    budget = LlmBudget(max_llm_calls=2)
    budget.reserve_llm_calls(2)

    with pytest.raises(BudgetExhaustedError, match="budget exhausted"):
        budget.reserve_llm_calls()


def test_budget_rejects_non_positive_reservation() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        LlmBudget(max_llm_calls=2).reserve_llm_calls(0)


def test_format_error_is_bounded_and_typed() -> None:
    message = format_error(RuntimeError("boom" * 1000))

    assert message.startswith("RuntimeError: ")
    assert len(message) == 2000


class _FakeStage:
    def __init__(self, name: StageName, *, error: Exception | None = None) -> None:
        self.name = name
        self._error = error
        self.calls = 0

    async def run(self, ctx: JobContext) -> StageStats:
        self.calls += 1
        stats = StageStats()
        stats.add("processed", 2)
        if self._error is not None:
            raise self._error
        return stats


def _context() -> JobContext:
    return JobContext(
        settings=MagicMock(),
        engine=MagicMock(),
        session_factory=MagicMock(),
        identity=WorkerIdentity(hostname="host", pid=1),
        budget=LlmBudget(max_llm_calls=1),
    )


@asynccontextmanager
async def _acquired(_engine: object, _key: int) -> AsyncGenerator[bool]:
    yield True


def test_runner_returns_empty_for_no_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    opened = MagicMock()
    monkeypatch.setattr("hermes_worker.jobs.runner.advisory_lock", opened)

    results = asyncio.run(
        run_stages(_context(), [], lock_name=LockName.MAINTAIN_EVENTS)
    )

    assert results == []
    opened.assert_not_called()


def test_runner_runs_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "hermes_worker.jobs.runner.advisory_lock",
        _acquired,
    )
    ctx = _context()
    stage = _FakeStage(StageName.HEALTHCHECK)

    results = asyncio.run(run_stages(ctx, [stage], lock_name=LockName.HEALTHCHECK))

    assert stage.calls == 1
    assert len(results) == 1
    assert results[0].outcome is StageOutcome.SUCCEEDED
    assert results[0].counters == {"processed": 2}


def test_runner_reraises_stage_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "hermes_worker.jobs.runner.advisory_lock",
        _acquired,
    )
    ctx = _context()
    stage = _FakeStage(StageName.REQUEUE_CLAIMS, error=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(run_stages(ctx, [stage], lock_name=LockName.MAINTAIN_EVENTS))


def test_runner_skips_when_lock_is_held(monkeypatch: pytest.MonkeyPatch) -> None:
    @asynccontextmanager
    async def _held(_engine: object, _key: int) -> AsyncGenerator[bool]:
        yield False

    monkeypatch.setattr(
        "hermes_worker.jobs.runner.advisory_lock",
        _held,
    )
    ctx = _context()
    stage = _FakeStage(StageName.REQUEUE_CLAIMS)

    results = asyncio.run(run_stages(ctx, [stage], lock_name=LockName.MAINTAIN_EVENTS))

    assert stage.calls == 0
    assert results[0].outcome is StageOutcome.SKIPPED
    assert results[0].counters == {}


def test_runner_without_lock_does_not_touch_advisory_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened = MagicMock()
    monkeypatch.setattr("hermes_worker.jobs.runner.advisory_lock", opened)
    stage = _FakeStage(StageName.HEALTHCHECK)

    results = asyncio.run(run_stages(_context(), [stage]))

    assert results[0].outcome is StageOutcome.SUCCEEDED
    opened.assert_not_called()


def test_runner_flushes_telemetry_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "hermes_worker.jobs.runner.advisory_lock",
        _acquired,
    )
    ctx = _context()
    ctx.ai = MagicMock()
    ctx.ai.aclose = AsyncMock()

    asyncio.run(run_stages(ctx, [_FakeStage(StageName.HEALTHCHECK)]))

    ctx.ai.aclose.assert_awaited_once()

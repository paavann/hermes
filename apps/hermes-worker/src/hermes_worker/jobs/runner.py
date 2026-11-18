from __future__ import annotations
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from hermes_worker.jobs.context import (
    JobContext,
    Stage,
    StageName,
    StageOutcome,
)
from hermes_worker.jobs.locks import LockName, advisory_lock, lock_key


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StageResult:
    stage: StageName
    outcome: StageOutcome
    counters: dict[str, int]


def format_error(exc: BaseException) -> str:
    message = f"{type(exc).__name__}: {exc}".strip()
    return message[:2000]


async def _run_sequence(
    ctx: JobContext,
    stages: Sequence[Stage],
) -> list[StageResult]:
    results: list[StageResult] = []
    try:
        for stage in stages:
            logger.info("starting job stage %s.", stage.name.value)
            try:
                stats = await stage.run(ctx)
            except BaseException as exc:
                logger.error(
                    "job stage %s failed: %s.",
                    stage.name.value,
                    format_error(exc),
                )
                raise
            logger.info(
                "finished job stage %s: %s.",
                stage.name.value,
                stats.counters,
            )
            results.append(
                StageResult(
                    stage=stage.name,
                    outcome=StageOutcome.SUCCEEDED,
                    counters=dict(stats.counters),
                )
            )
    finally:
        await ctx.flush_telemetry()
    return results


async def run_stages(
    ctx: JobContext,
    stages: Sequence[Stage],
    *,
    lock_name: LockName | None = None,
) -> list[StageResult]:
    """Run stages in order, optionally under one advisory lock."""
    if not stages:
        return []

    if lock_name is None:
        return await _run_sequence(ctx, stages)

    async with advisory_lock(ctx.engine, lock_key(lock_name)) as acquired:
        if not acquired:
            return [
                StageResult(
                    stage=stage.name,
                    outcome=StageOutcome.SKIPPED,
                    counters={},
                )
                for stage in stages
            ]
        return await _run_sequence(ctx, stages)

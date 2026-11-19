from __future__ import annotations
import logging
from collections.abc import Sequence
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import Stage, create_job_context
from hermes_worker.jobs.locks import LockName
from hermes_worker.jobs.runner import StageResult, run_stages
from hermes_worker.jobs.stages import (
    AnalyzeStage,
    EventLifecycleStage,
    HealthcheckStage,
    IngestStage,
    RequeueStaleClaimsStage,
)


logger = logging.getLogger(__name__)


MAINTAIN_STAGES: tuple[Stage, ...] = (
    RequeueStaleClaimsStage(),
    EventLifecycleStage(),
)
HEALTHCHECK_STAGES: tuple[Stage, ...] = (HealthcheckStage(),)


def _summarize(results: Sequence[StageResult]) -> str:
    if not results:
        return "no stages"
    return ", ".join(
        f"{result.stage.value}={result.outcome.value}" for result in results
    )


async def run_ingest_articles(*, settings: Settings, force: bool) -> None:
    async with create_job_context(settings, with_ai=True) as ctx:
        results = await run_stages(
            ctx,
            (IngestStage(force=force), AnalyzeStage()),
            lock_name=LockName.INGEST_ARTICLES,
        )
    logger.info("ingest-articles finished: %s.", _summarize(results))


async def run_maintain_events(settings: Settings) -> None:
    async with create_job_context(settings) as ctx:
        results = await run_stages(
            ctx,
            MAINTAIN_STAGES,
            lock_name=LockName.MAINTAIN_EVENTS,
        )
    logger.info("maintain-events finished: %s.", _summarize(results))


async def run_healthcheck(*, settings: Settings) -> None:
    async with create_job_context(settings) as ctx:
        results = await run_stages(ctx, HEALTHCHECK_STAGES)
    logger.info("healthcheck finished: %s.", _summarize(results))

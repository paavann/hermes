from __future__ import annotations
import logging
from collections.abc import Sequence
from datetime import datetime
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import Stage, create_job_context
from hermes_worker.jobs.locks import LockName
from hermes_worker.jobs.runner import StageResult, run_stages
from hermes_worker.jobs.stages import (
    AnalyzeStage,
    ClusterStage,
    DescribeStage,
    EventLifecycleStage,
    HealthcheckStage,
    IngestStage,
    MaintenanceStage,
    ReconcileStage,
    RequeueArticlesStage,
    RequeueStaleClaimsStage,
    ScoreStage,
    ThreadLifecycleStage,
    ThreadStage,
)


logger = logging.getLogger(__name__)


BUILD_STAGES: tuple[Stage, ...] = (
    ClusterStage(),
    DescribeStage(),
    ScoreStage(),
    ThreadStage(),
    ReconcileStage(),
)
MAINTAIN_STAGES: tuple[Stage, ...] = (
    RequeueStaleClaimsStage(),
    EventLifecycleStage(),
    ThreadLifecycleStage(),
    MaintenanceStage(),
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


async def run_build_events(settings: Settings) -> None:
    async with create_job_context(
        settings,
        with_ai=True,
        with_geocoder=True,
    ) as ctx:
        results = await run_stages(
            ctx,
            BUILD_STAGES,
            lock_name=LockName.BUILD_EVENTS,
        )
    logger.info("build-events finished: %s.", _summarize(results))


async def run_maintain_events(
    settings: Settings,
    *,
    requeue_since: datetime | None = None,
) -> None:
    stages: tuple[Stage, ...] = MAINTAIN_STAGES
    if requeue_since is not None:
        stages = (RequeueArticlesStage(since=requeue_since), *MAINTAIN_STAGES)
    async with create_job_context(settings) as ctx:
        results = await run_stages(
            ctx,
            stages,
            lock_name=LockName.MAINTAIN_EVENTS,
        )
    logger.info("maintain-events finished: %s.", _summarize(results))


async def run_healthcheck(*, settings: Settings) -> None:
    async with create_job_context(settings) as ctx:
        results = await run_stages(ctx, HEALTHCHECK_STAGES)
    logger.info("healthcheck finished: %s.", _summarize(results))

from __future__ import annotations
from datetime import UTC, datetime, timedelta
from hermes_db.services import (
    EventLifecycleService,
    MaintenanceService,
    ThreadService,
)
from hermes_worker.jobs.context import JobContext, StageName, StageStats
from hermes_worker.jobs.queue import ArticleQueue


RECONCILE_PAGE_SIZE = 1000


class RequeueStaleClaimsStage:
    """Return abandoned article claims to the queue."""

    name = StageName.REQUEUE_CLAIMS

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()
        older_than = datetime.now(UTC) - timedelta(
            minutes=ctx.settings.ARTICLE_CLAIM_STALE_MINUTES
        )

        async with ctx.session_factory() as session:
            queue = ArticleQueue(session)
            while True:
                requeued, failed = await queue.requeue_stale(
                    older_than=older_than,
                    limit=ctx.settings.ARTICLE_CLAIM_BATCH_SIZE,
                    max_attempts=ctx.settings.ARTICLE_MAX_ATTEMPTS,
                )
                stats.add("requeued", requeued)
                stats.add("failed", failed)
                if requeued + failed < ctx.settings.ARTICLE_CLAIM_BATCH_SIZE:
                    break
            await session.commit()

        return stats


class RequeueArticlesStage:
    """Reset failed and rejected articles so analysis can retry them."""

    name = StageName.REQUEUE_ARTICLES

    def __init__(self, *, since: datetime) -> None:
        self._since = since

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()
        async with ctx.session_factory() as session:
            requeued = await MaintenanceService(session).requeue_articles(
                since=self._since
            )
            await session.commit()
        stats.add("requeued", requeued)
        return stats


class EventLifecycleStage:
    """Move stale and archived events through the retention state machine."""

    name = StageName.EVENT_LIFECYCLE

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()

        async with ctx.session_factory() as session:
            result = await EventLifecycleService(session).run(
                stale_hours=ctx.settings.EVENT_STALE_HOURS,
                archive_hours=ctx.settings.EVENT_ARCHIVE_HOURS,
            )
            await session.commit()

        stats.add("staled", result.staled)
        stats.add("archived", result.archived)
        return stats


class ThreadLifecycleStage:
    """Move quiet story threads to dormant and then ended."""

    name = StageName.THREAD_LIFECYCLE

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()

        async with ctx.session_factory() as session:
            result = await ThreadService(session).run_lifecycle()
            await session.commit()

        stats.add("dormant", result["dormant"])
        stats.add("ended", result["ended"])
        return stats


class MaintenanceStage:
    """Reconcile aggregates, apply retention, and report drift."""

    name = StageName.MAINTENANCE

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()

        async with ctx.session_factory() as session:
            service = MaintenanceService(session)
            after_id = None
            while True:
                event_ids = await service.reconcile_counts(
                    after_id=after_id,
                    limit=RECONCILE_PAGE_SIZE,
                )
                stats.add("reconciled", len(event_ids))
                await session.commit()
                if len(event_ids) < RECONCILE_PAGE_SIZE:
                    break
                after_id = event_ids[-1]

            retention = await service.apply_retention()
            await session.commit()
            report = await service.consistency_report()

        stats.add("retention_cluster_decisions", retention.cluster_decisions)
        stats.add("retention_event_members", retention.removed_members)
        stats.add("retention_embeddings", retention.archived_embeddings)
        stats.add("count_drift", report.count_drift)
        stats.add("events_without_members", report.events_without_members)
        stats.add("missing_embeddings", report.missing_embeddings)
        stats.add("failed_claims", report.failed_claims)
        stats.add("orphan_labels", report.orphan_labels)
        return stats

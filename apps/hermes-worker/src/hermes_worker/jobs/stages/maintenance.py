from __future__ import annotations
from datetime import UTC, datetime, timedelta
from hermes_db.services import EventService
from hermes_worker.jobs.context import JobContext, StageName, StageStats
from hermes_worker.jobs.queue import ArticleQueue


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


class EventLifecycleStage:
    """Apply score decay and event status transitions."""

    name = StageName.EVENT_LIFECYCLE

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()

        async with ctx.session_factory() as session:
            result = await EventService(session).run_lifecycle_transitions(
                stale_hours=ctx.settings.EVENT_STALE_HOURS,
                archive_hours=ctx.settings.EVENT_ARCHIVE_HOURS,
            )
            await session.commit()

        stats.add("staled", result["staled"])
        stats.add("archived", result["archived"])
        return stats

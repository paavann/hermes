from __future__ import annotations
from datetime import UTC, datetime
from hermes_db.services import EventScoringService
from hermes_worker.jobs.context import JobContext, StageName, StageStats


class ScoreStage:
    """Recompute the single importance score for every active event."""

    name = StageName.SCORE

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()
        now = datetime.now(UTC)
        page_size = ctx.settings.EVENT_SCORE_PAGE_SIZE
        after_id = None

        while True:
            async with ctx.session_factory() as session:
                service = EventScoringService(session)
                states = await service.active_states(
                    after_id=after_id,
                    limit=page_size,
                )
                for state in states:
                    result = await service.rescore(state.id, now=now)
                    if result is None:
                        stats.add("missing")
                        continue
                    stats.add("scored")
                    if result.capped:
                        stats.add("capped_single_source")
                    if result.breaking_override:
                        stats.add("breaking")
                await session.commit()

            if len(states) < page_size:
                break
            after_id = states[-1].id

        return stats

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import ClusterDecisionKind
from hermes_db.models.cluster_decision import ClusterDecision


class ClusterDecisionService:
    """Reads and writes cached pairwise adjudications.

    Decisions are content-addressed by ``pair_hash``; callers include the
    article id, event id, and event member hash so a changed cluster misses.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, pair_hash: str) -> ClusterDecision | None:
        stmt = select(ClusterDecision).where(
            ClusterDecision.pair_hash == pair_hash
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def save(
        self,
        *,
        pair_hash: str,
        decision: ClusterDecisionKind,
        confidence: float | None,
        model: str | None,
        prompt_version: str | None,
    ) -> ClusterDecision:
        values = {
            "pair_hash": pair_hash,
            "decision": decision,
            "confidence": confidence,
            "model": model,
            "prompt_version": prompt_version,
            "created_at": datetime.now(UTC),
        }
        stmt = (
            pg_insert(ClusterDecision)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["pair_hash"],
                set_={
                    "decision": decision,
                    "confidence": confidence,
                    "model": model,
                    "prompt_version": prompt_version,
                },
            )
            .returning(ClusterDecision)
        )
        return (await self._session.execute(stmt)).scalar_one()

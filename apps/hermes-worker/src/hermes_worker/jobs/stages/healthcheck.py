from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final
from hermes_db.enums import IngestStatus
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_worker.jobs.context import JobContext, StageName, StageStats
from hermes_worker.jobs.errors import SchemaCheckError
from hermes_worker.jobs.queue import ArticleQueue


EXPECTED_COLUMNS: Final[dict[str, frozenset[str]]] = {
    "articles": frozenset(
        {
            "claimed_at",
            "claimed_by",
            "attempt_count",
            "last_error",
        }
    ),
}

_COLUMNS_SQL = text(
    "SELECT table_name, column_name "
    "FROM information_schema.columns "
    "WHERE table_schema = 'public' "
    "AND table_name = 'articles'"
)
_INGEST_CONSTRAINT_SQL = text(
    "SELECT pg_get_constraintdef(c.oid) "
    "FROM pg_constraint c "
    "JOIN pg_class t ON t.oid = c.conrelid "
    "WHERE t.relname = 'articles' AND c.conname = 'ingeststatus'"
)
_CLAIM_INDEX_SQL = text(
    "SELECT to_regclass('public.idx_articles_analyzing_claimed_at') IS NOT NULL"
)


@dataclass(frozen=True, slots=True)
class SchemaReport:
    missing: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing


def evaluate_schema(
    *,
    columns: Mapping[str, set[str]],
    ingest_constraint: str | None,
    claim_index_exists: bool,
) -> SchemaReport:
    missing: list[str] = []
    for table, expected in EXPECTED_COLUMNS.items():
        present = columns.get(table, set())
        for column in sorted(expected - present):
            missing.append(f"{table}.{column}")

    if ingest_constraint is None:
        missing.append("articles.ingeststatus")
    else:
        for value in ("ANALYZING", "FAILED"):
            if f"'{value}'" not in ingest_constraint:
                missing.append(f"articles.ingest_status[{value}]")

    if not claim_index_exists:
        missing.append("articles.idx_articles_analyzing_claimed_at")

    return SchemaReport(tuple(missing))


async def _load_columns(session: AsyncSession) -> dict[str, set[str]]:
    rows = (await session.execute(_COLUMNS_SQL)).all()
    columns: dict[str, set[str]] = {}
    for table_name, column_name in rows:
        columns.setdefault(table_name, set()).add(column_name)
    return columns


async def _load_ingest_constraint(session: AsyncSession) -> str | None:
    value = await session.scalar(_INGEST_CONSTRAINT_SQL)
    return str(value) if value is not None else None


class HealthcheckStage:
    name = StageName.HEALTHCHECK

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()
        now = datetime.now(UTC)

        async with ctx.session_factory() as session:
            await session.execute(text("SELECT 1"))
            stats.add("db_ok")

            report = evaluate_schema(
                columns=await _load_columns(session),
                ingest_constraint=await _load_ingest_constraint(session),
                claim_index_exists=bool(await session.scalar(_CLAIM_INDEX_SQL)),
            )
            stats.add("schema_ok", 1 if report.ok else 0)
            if not report.ok:
                stats.add("schema_missing", len(report.missing))
                raise SchemaCheckError(
                    f"worker schema is incomplete: {', '.join(report.missing)}."
                )

            queue = ArticleQueue(session)
            counts = await queue.status_counts()
            for status in IngestStatus:
                stats.add(
                    f"queue_{status.value.lower()}",
                    counts.get(status, 0),
                )
            stale_before = now - timedelta(
                minutes=ctx.settings.ARTICLE_CLAIM_STALE_MINUTES
            )
            stats.add(
                "stale_claims",
                await queue.count_stale(older_than=stale_before),
            )

        return stats

"""Unit and integration tests for the article claim queue."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
import pytest
from hermes_db.enums import IngestStatus
from hermes_db.models.article import Article
from sqlalchemy import delete, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker
from hermes_worker.jobs.queue import ArticleQueue
from tests.integration_utils import make_engine, require_schema


def _article(
    suffix: str,
    *,
    status: IngestStatus = IngestStatus.NEW,
    claimed_at: datetime | None = None,
    attempt_count: int = 0,
) -> Article:
    unique = uuid.uuid4().hex
    return Article(
        title=f"Queue test {suffix}",
        url=f"https://example.com/{suffix}-{unique}",
        published_at=datetime.now(UTC),
        ingest_status=status,
        claimed_at=claimed_at,
        attempt_count=attempt_count,
    )


class TestClaimStatement:
    def test_uses_skip_locked_limit_and_returning(self) -> None:
        stmt = ArticleQueue.claim_statement(
            status=IngestStatus.NEW,
            limit=10,
            worker_id="worker-a",
            max_attempts=3,
        )
        sql = str(
            stmt.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )

        assert "FOR UPDATE SKIP LOCKED" in sql
        assert "LIMIT 10" in sql
        assert "attempt_count < 3" in sql
        assert "RETURNING" in sql
        assert "worker-a" in sql
        assert "ANALYZING" in sql

    def test_rejects_non_positive_limit(self) -> None:
        with pytest.raises(ValueError, match="claim limit"):
            ArticleQueue.claim_statement(
                status=IngestStatus.NEW,
                limit=0,
                worker_id="worker-a",
                max_attempts=3,
            )


@pytest.mark.integration
def test_claim_skips_rows_held_by_another_worker() -> None:
    async def run() -> None:
        engine = make_engine()
        await require_schema(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        ids: list[uuid.UUID] = []
        try:
            async with factory() as session:
                articles = [_article("a"), _article("b"), _article("c")]
                session.add_all(articles)
                await session.commit()
                ids = [article.id for article in articles]

            async with factory() as session:
                first = await ArticleQueue(session).claim(
                    status=IngestStatus.NEW,
                    limit=2,
                    worker_id="worker-a",
                    max_attempts=3,
                )
                await session.commit()

            async with factory() as session:
                second = await ArticleQueue(session).claim(
                    status=IngestStatus.NEW,
                    limit=2,
                    worker_id="worker-b",
                    max_attempts=3,
                )
                await session.commit()

            assert len(first) == 2
            assert len(second) == 1
            assert {article.id for article in first}.isdisjoint(
                {article.id for article in second}
            )
            assert all(
                article.ingest_status is IngestStatus.ANALYZING for article in first
            )
            assert all(
                article.attempt_count == 1 and article.claimed_by == "worker-a"
                for article in first
            )

            async with factory() as session:
                changed = await ArticleQueue(session).mark(
                    ids,
                    IngestStatus.LABELED,
                )
                await session.commit()
                counts = await ArticleQueue(session).status_counts()

            assert changed == 3
            assert counts[IngestStatus.LABELED] >= 3
        finally:
            async with factory() as session:
                if ids:
                    await session.execute(delete(Article).where(Article.id.in_(ids)))
                    await session.commit()
            await engine.dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_requeue_stale_returns_or_fails_articles() -> None:
    async def run() -> None:
        engine = make_engine()
        await require_schema(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        ids: list[uuid.UUID] = []
        try:
            stale_at = datetime.now(UTC) - timedelta(hours=1)
            async with factory() as session:
                requeue = _article(
                    "requeue",
                    status=IngestStatus.ANALYZING,
                    claimed_at=stale_at,
                    attempt_count=1,
                )
                exhausted = _article(
                    "exhausted",
                    status=IngestStatus.ANALYZING,
                    claimed_at=stale_at,
                    attempt_count=3,
                )
                session.add_all([requeue, exhausted])
                await session.commit()
                ids = [requeue.id, exhausted.id]

            async with factory() as session:
                requeued, failed = await ArticleQueue(session).requeue_stale(
                    older_than=datetime.now(UTC) - timedelta(minutes=30),
                    limit=10,
                    max_attempts=3,
                )
                await session.commit()

            assert (requeued, failed) == (1, 1)

            async with factory() as session:
                rows = (
                    await session.execute(
                        select(Article.id, Article.ingest_status).where(
                            Article.id.in_(ids)
                        )
                    )
                ).all()
            statuses = dict(rows)
            assert statuses[ids[0]] is IngestStatus.NEW
            assert statuses[ids[1]] is IngestStatus.FAILED
        finally:
            async with factory() as session:
                if ids:
                    await session.execute(delete(Article).where(Article.id.in_(ids)))
                    await session.commit()
            await engine.dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_fail_retries_until_attempts_are_exhausted() -> None:
    async def run() -> None:
        engine = make_engine()
        await require_schema(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        ids: list[uuid.UUID] = []
        try:
            async with factory() as session:
                retry = _article("retry", attempt_count=1)
                exhausted = _article("final", attempt_count=3)
                session.add_all([retry, exhausted])
                await session.commit()
                ids = [retry.id, exhausted.id]

                queue = ArticleQueue(session)
                retry_status = await queue.fail(
                    retry,
                    "temporary failure.",
                    max_attempts=3,
                )
                exhausted_status = await queue.fail(
                    exhausted,
                    "permanent failure.",
                    max_attempts=3,
                )
                await session.commit()

            assert retry_status is IngestStatus.NEW
            assert exhausted_status is IngestStatus.FAILED

            async with factory() as session:
                rows = (
                    await session.execute(
                        select(
                            Article.id, Article.ingest_status, Article.last_error
                        ).where(Article.id.in_(ids))
                    )
                ).all()
            by_id = {row[0]: row for row in rows}
            assert by_id[ids[0]][1] is IngestStatus.NEW
            assert by_id[ids[0]][2] == "temporary failure."
            assert by_id[ids[1]][1] is IngestStatus.FAILED
            assert by_id[ids[1]][2] == "permanent failure."
        finally:
            async with factory() as session:
                if ids:
                    await session.execute(delete(Article).where(Article.id.in_(ids)))
                    await session.commit()
            await engine.dispose()

    asyncio.run(run())

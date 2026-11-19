from __future__ import annotations
import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from itertools import batched
from hermes_ai import ConfigurationError
from hermes_ai.models.labels import ArticleLabelBatchResponse, LabelArticleInput
from hermes_db.enums import ArticleBodySource, IngestStatus, SourceFetchPolicy
from hermes_db.services import (
    AnalysisArticle,
    ArticleAnalysisService,
    ArticleFamilyService,
    ArticleLabelService,
    FamilyCandidate,
)
from hermes_worker.jobs.context import (
    BudgetExhaustedError,
    JobContext,
    StageName,
    StageStats,
)
from hermes_worker.jobs.families import find_family, origin_group
from hermes_worker.jobs.fetch import BodyFetcher, FetchResult
from hermes_worker.jobs.labels import (
    GateDecision,
    LabelPayload,
    build_embedding_text,
    build_label_input,
    build_text_hashes,
    embedding_input_hash,
    evaluate_gate,
    label_input_hash,
    payload_from_row,
    select_text,
    to_label_payload,
)
from hermes_worker.jobs.queue import ArticleQueue
from hermes_worker.jobs.runner import format_error


logger = logging.getLogger(__name__)


class AnalyzeStage:
    """Fetch article text transiently, label it, embed it, and assign a family."""

    name = StageName.ANALYZE

    def __init__(self, *, fetcher: BodyFetcher | None = None) -> None:
        self._fetcher = fetcher

    async def run(self, ctx: JobContext) -> StageStats:
        settings = ctx.settings
        stats = StageStats()
        max_batches = ctx.budget.remaining_llm_calls
        max_articles = min(
            settings.ARTICLE_ANALYZE_BATCH_SIZE,
            max_batches * settings.ARTICLE_LABEL_BATCH_SIZE,
        )
        if max_articles <= 0:
            stats.add("budget_empty")
            return stats

        article_ids = await self._claim(ctx, max_articles)
        stats.add("claimed", len(article_ids))
        if not article_ids:
            return stats

        async with ctx.session_factory() as session:
            articles = await ArticleAnalysisService(session).load_for_analysis(
                article_ids
            )
        stats.add("loaded", len(articles))

        owned_fetcher = self._fetcher is None
        fetcher = self._fetcher or BodyFetcher(
            user_agent=settings.NOMINATIM_USER_AGENT,
            connect_timeout=settings.ARTICLE_FETCH_CONNECT_TIMEOUT_SECONDS,
            read_timeout=settings.ARTICLE_FETCH_READ_TIMEOUT_SECONDS,
            max_bytes=settings.ARTICLE_FETCH_MAX_BYTES,
            max_redirects=settings.ARTICLE_FETCH_MAX_REDIRECTS,
            per_host_concurrency=settings.ARTICLE_FETCH_PER_HOST_CONCURRENCY,
            min_body_chars=settings.ARTICLE_BODY_MIN_CHARS,
        )
        try:
            for group in batched(
                articles,
                settings.ARTICLE_LABEL_BATCH_SIZE,
                strict=False,
            ):
                try:
                    await self._process_group(ctx, list(group), fetcher, stats)
                except BudgetExhaustedError:
                    await self._release(ctx, [article.id for article in group])
                    stats.add("budget_exhausted")
                    logger.warning("llm budget exhausted during analyze.")
                    return stats
                except ConfigurationError:
                    raise
                except Exception as exc:
                    logger.error(
                        "analyze group failed: %s.",
                        format_error(exc),
                        exc_info=True,
                    )
                    await self._fail_articles(
                        ctx,
                        [(article, format_error(exc)) for article in group],
                        stats,
                    )
        finally:
            if owned_fetcher:
                await fetcher.aclose()

        return stats

    async def _claim(
        self,
        ctx: JobContext,
        limit: int,
    ) -> list[uuid.UUID]:
        async with ctx.session_factory() as session:
            queue = ArticleQueue(session)
            claimed = await queue.claim(
                status=IngestStatus.NEW,
                limit=limit,
                worker_id=ctx.identity.id,
                max_attempts=ctx.settings.ARTICLE_MAX_ATTEMPTS,
            )
            await session.commit()
        return [article.id for article in claimed]

    async def _process_group(
        self,
        ctx: JobContext,
        articles: list[AnalysisArticle],
        fetcher: BodyFetcher,
        stats: StageStats,
    ) -> None:
        if not articles:
            return
        settings = ctx.settings
        ai = ctx.require_ai()
        labeler = ai.labels
        model_name = labeler.model_name or settings.LLM_MODEL or "unknown"

        fetched = await asyncio.gather(
            *(self._fetch_one(fetcher, article, stats) for article in articles)
        )
        selected = [
            select_text(article, result)
            for article, result in zip(articles, fetched, strict=True)
        ]
        for text in selected:
            if text.body_source is None:
                stats.add("text_missing")
            else:
                stats.add(f"text_{text.body_source.value.lower()}")

        async with ctx.session_factory() as session:
            analysis = ArticleAnalysisService(session)
            for article, text in zip(articles, selected, strict=True):
                title_hash, body_hash = build_text_hashes(
                    title=article.title,
                    text=text.text,
                )
                await analysis.save_text(
                    article.id,
                    body_source=text.body_source,
                    body_simhash=body_hash,
                    title_simhash=title_hash,
                    word_count=text.word_count,
                    input_quality=text.input_quality,
                    fetch_http_status=text.http_status,
                )
            await session.commit()

        async with ctx.session_factory() as session:
            rows = await ArticleLabelService(session).list_labels(
                [article.id for article in articles],
                labeler.prompt_version,
            )
        existing = {row.article_id: row for row in rows}

        selected_by_id = {
            article.id: text
            for article, text in zip(articles, selected, strict=True)
        }
        digest_by_id: dict[uuid.UUID, str] = {}
        inputs_to_label: list[LabelArticleInput] = []
        owner_by_index: dict[int, uuid.UUID] = {}
        payloads: dict[uuid.UUID, LabelPayload] = {}
        reused = 0

        for index, (article, text) in enumerate(
            zip(articles, selected, strict=True)
        ):
            label_input = build_label_input(
                index=index,
                article=article,
                body=(
                    text.text
                    if text.body_source == ArticleBodySource.FULL_TEXT
                    else None
                ),
            )
            digest = label_input_hash(label_input)
            digest_by_id[article.id] = digest
            row = existing.get(article.id)
            if row is not None and row.input_hash == digest:
                payloads[article.id] = payload_from_row(row)
                reused += 1
                continue
            inputs_to_label.append(label_input)
            owner_by_index[label_input.index] = article.id

        stats.add("labels_reused", reused)
        failures: list[tuple[AnalysisArticle, str]] = []
        article_by_id = {article.id: article for article in articles}

        if inputs_to_label:
            ctx.budget.reserve_llm_calls(1)
            stats.add("label_calls")
            response = await labeler.label(inputs_to_label)
            if response is None:
                for article_id in owner_by_index.values():
                    failures.append((article_by_id[article_id], "labeler failed"))
            else:
                before = len(payloads)
                self._merge_labels(
                    response=response,
                    owner_by_index=owner_by_index,
                    digest_by_id=digest_by_id,
                    payloads=payloads,
                )
                stats.add("labels_new", len(payloads) - before)
                for article_id in owner_by_index.values():
                    if article_id not in payloads:
                        failures.append(
                            (article_by_id[article_id], "labeler missing index")
                        )

        decisions: dict[uuid.UUID, GateDecision] = {}
        accepted: list[tuple[AnalysisArticle, LabelPayload]] = []
        for article in articles:
            payload = payloads.get(article.id)
            if payload is None:
                continue
            decision = evaluate_gate(payload)
            decisions[article.id] = decision
            if decision.rejected:
                stage_name = decision.stage.value.lower() if decision.stage else "gate"
                stats.add(f"rejected_{stage_name}")
            else:
                accepted.append((article, payload))

        embedding_text_by_id: dict[uuid.UUID, str] = {}
        vectors: dict[uuid.UUID, list[float]] = {}
        if accepted:
            texts: list[str] = []
            for article, payload in accepted:
                text = build_embedding_text(payload, title=article.title)
                embedding_text_by_id[article.id] = text
                texts.append(text)
            results = await ai.llm.gen_embeddings(texts)
            stats.add("embed_calls")
            for (article, _payload), vector in zip(
                accepted,
                results,
                strict=True,
            ):
                if vector is None:
                    stats.add("embed_failed")
                else:
                    vectors[article.id] = vector
                    stats.add("embedded")

        now = datetime.now(UTC)
        candidate_since = now - timedelta(days=settings.ARTICLE_FAMILY_WINDOW_DAYS)
        async with ctx.session_factory() as session:
            labels = ArticleLabelService(session)
            analysis = ArticleAnalysisService(session)
            families = ArticleFamilyService(session)
            candidates: list[FamilyCandidate] = []
            if accepted:
                candidates = await families.recent_candidates(
                    since=candidate_since,
                    limit=settings.ARTICLE_FAMILY_MAX_CANDIDATES,
                )

            for article in articles:
                payload = payloads.get(article.id)
                if payload is None:
                    continue
                await labels.upsert_label(
                    article.id,
                    labeler.prompt_version,
                    model_name,
                    payload,
                )
                decision = decisions[article.id]
                if decision.rejected:
                    await analysis.finalize(
                        article.id,
                        status=IngestStatus.REJECTED,
                        reject_stage=decision.stage,
                        reject_reason=decision.reason,
                    )
                    continue

                vector = vectors.get(article.id)
                if vector is None:
                    retry_status = (
                        IngestStatus.NEW
                        if article.attempt_count < settings.ARTICLE_MAX_ATTEMPTS
                        else IngestStatus.FAILED
                    )
                    stats.add(
                        "embed_retry"
                        if retry_status == IngestStatus.NEW
                        else "embed_terminal"
                    )
                    await analysis.finalize(
                        article.id,
                        status=retry_status,
                        error="embedding unavailable",
                    )
                    continue

                text = selected_by_id[article.id]
                await analysis.save_embedding(
                    article.id,
                    model=settings.EMBED_MODEL or "unknown",
                    embedding=vector,
                    input_hash=embedding_input_hash(
                        embedding_text_by_id[article.id]
                    ),
                )
                title_hash, body_hash = build_text_hashes(
                    title=article.title,
                    text=text.text,
                )
                if article.family_id is not None:
                    stats.add("family_existing")
                elif title_hash is None:
                    stats.add("family_skipped")
                else:
                    origin = origin_group(
                        source_origin_group=article.source_origin_group,
                        source_slug=article.source_slug,
                    )
                    event_time = payload.event_time or article.published_at
                    match = find_family(
                        candidates,
                        title_simhash=title_hash,
                        body_simhash=body_hash,
                        embedding=vector,
                        event_time=event_time,
                    )
                    if match is not None:
                        adopt = (
                            event_time is not None
                            and match.representative_time is not None
                            and event_time < match.representative_time
                        )
                        await families.add_member(
                            family_id=match.family_id,
                            article_id=article.id,
                            title_simhash=title_hash,
                            body_simhash=body_hash,
                            origin_group=origin,
                            adopt_representative=adopt,
                        )
                        stats.add("family_members")
                    else:
                        family_id = await families.create(
                            article_id=article.id,
                            title_simhash=title_hash,
                            body_simhash=body_hash,
                            origin_group=origin,
                        )
                        candidates.append(
                            FamilyCandidate(
                                family_id=family_id,
                                representative_article_id=article.id,
                                title_simhash=title_hash,
                                body_simhash=body_hash,
                                origin_group=origin,
                                representative_time=event_time,
                                representative_embedding=tuple(vector),
                            )
                        )
                        stats.add("families_created")

                await analysis.finalize(
                    article.id,
                    status=IngestStatus.LABELED,
                )
            await session.commit()

        if failures:
            await self._fail_articles(ctx, failures, stats)

    @staticmethod
    def _merge_labels(
        *,
        response: ArticleLabelBatchResponse,
        owner_by_index: dict[int, uuid.UUID],
        digest_by_id: dict[uuid.UUID, str],
        payloads: dict[uuid.UUID, LabelPayload],
    ) -> None:
        for extraction in response.labels:
            article_id = owner_by_index.get(extraction.index)
            if article_id is None:
                logger.warning(
                    "dropping label for unknown batch index %s.",
                    extraction.index,
                )
                continue
            payloads[article_id] = to_label_payload(
                extraction,
                input_hash=digest_by_id[article_id],
            )

    @staticmethod
    async def _fetch_one(
        fetcher: BodyFetcher,
        article: AnalysisArticle,
        stats: StageStats,
    ) -> FetchResult | None:
        if article.paywall or article.fetch_policy != SourceFetchPolicy.FULL_TEXT:
            stats.add("fetch_skipped")
            return None
        result = await fetcher.fetch(article.url)
        stats.add("fetch_attempted")
        stats.add(f"fetch_{result.reason.value}")
        return result

    async def _fail_articles(
        self,
        ctx: JobContext,
        failures: list[tuple[AnalysisArticle, str]],
        stats: StageStats,
    ) -> None:
        async with ctx.session_factory() as session:
            queue = ArticleQueue(session)
            for article, error in failures:
                status = await queue.fail_id(
                    article_id=article.id,
                    attempt_count=article.attempt_count,
                    error=error[:2000],
                    max_attempts=ctx.settings.ARTICLE_MAX_ATTEMPTS,
                )
                stats.add(
                    "failed_terminal"
                    if status == IngestStatus.FAILED
                    else "failed_retry"
                )
            await session.commit()

    @staticmethod
    async def _release(
        ctx: JobContext,
        article_ids: list[uuid.UUID],
    ) -> None:
        async with ctx.session_factory() as session:
            await ArticleQueue(session).release(article_ids)
            await session.commit()

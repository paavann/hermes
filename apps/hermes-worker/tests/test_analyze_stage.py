import asyncio
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from hermes_ai.models.labels import (
    ArticleLabelBatchResponse,
    ArticleLabelExtraction,
    LabelArticleInput,
)
from hermes_db.enums import (
    ArticleBodySource,
    ArticleCategory,
    ArticleCertainty,
    ArticleType,
    EventForm,
    EventScope,
    IngestStatus,
    SourceFetchPolicy,
)
from hermes_db.services import AnalysisArticle
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import JobContext, LlmBudget, WorkerIdentity
from hermes_worker.jobs.fetch import FetchResult
from hermes_worker.jobs.labels import build_label_input, label_input_hash
from hermes_worker.jobs.stages.analyze import AnalyzeStage


NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
PROMPT_VERSION = "label-v1"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        DB_PASSWORD="worker-secret-pass",
        LLM_MODEL="test/label-model",
        EMBED_MODEL="test/embed-model",
        ARTICLE_LABEL_BATCH_SIZE=10,
        ARTICLE_ANALYZE_BATCH_SIZE=50,
    )


def _article(
    *,
    fetch_policy: SourceFetchPolicy = SourceFetchPolicy.SUMMARY_ONLY,
    paywall: bool = False,
    family_id: uuid.UUID | None = None,
    attempt_count: int = 0,
) -> AnalysisArticle:
    return AnalysisArticle(
        id=uuid.uuid4(),
        title="Earthquake strikes coastal city",
        url="https://news.example.com/story",
        feed_summary="Twelve people died after a magnitude 6.1 earthquake.",
        published_at=NOW,
        language="en",
        attempt_count=attempt_count,
        family_id=family_id,
        source_name="Example News",
        source_slug="example-news",
        source_origin_group="example",
        fetch_policy=fetch_policy,
        paywall=paywall,
    )


def _label(
    *,
    index: int = 0,
    is_event: bool = True,
    article_type: ArticleType = ArticleType.BREAKING,
    specificity: int = 4,
    reject_reason: str | None = None,
) -> ArticleLabelExtraction:
    return ArticleLabelExtraction(
        index=index,
        is_event=is_event,
        article_type=article_type.value,
        event_form=EventForm.INCIDENT.value if is_event else None,
        category=ArticleCategory.DISASTER.value,
        specificity=specificity,
        consequence=4,
        certainty=ArticleCertainty.REPORTED.value,
        fact=(
            "A magnitude 6.1 earthquake struck the coastal city on Tuesday."
            if is_event
            else None
        ),
        event_time=NOW,
        locations=[{"name": "Coastal City", "country_code": "EX"}],
        entities=[{"name": "Coastal City", "kind": "LOCATION"}],
        scale_facts={"deaths": 12},
        severity=4,
        scope=EventScope.CITY.value,
        confidence=0.9,
        evidence_quote="A magnitude 6.1 earthquake struck the coastal city.",
        reject_reason=reject_reason,
    )


class _Labeler:
    prompt_version = PROMPT_VERSION
    model_name = "test/label-model"

    def __init__(self, response: ArticleLabelBatchResponse | None) -> None:
        self.response = response
        self.calls: list[list[LabelArticleInput]] = []

    async def label(
        self,
        inputs: list[LabelArticleInput],
    ) -> ArticleLabelBatchResponse | None:
        self.calls.append(inputs)
        return self.response


class _Embedder:
    def __init__(self, *, available: bool = True) -> None:
        self.calls: list[list[str]] = []
        self.input_types: list[str] = []
        self._available = available

    async def gen_embeddings(
        self, texts: list[str], input_type: str = "passage"
    ) -> list[list[float] | None]:
        self.calls.append(texts)
        self.input_types.append(input_type)
        if not self._available:
            return [None] * len(texts)
        return [[1.0, 0.0, 0.0] for _ in texts]


class _Ai:
    def __init__(
        self,
        response: ArticleLabelBatchResponse | None,
        *,
        embedding_available: bool = True,
    ) -> None:
        self.labels = _Labeler(response)
        self.llm = _Embedder(available=embedding_available)


class _Fetcher:
    def __init__(self) -> None:
        self.calls = 0

    async def fetch(self, url: str) -> FetchResult:
        self.calls += 1
        raise AssertionError(f"unexpected fetch for {url}")


def _session_factory(
    sessions: list[AsyncMock],
) -> Callable[[], AsyncMock]:
    def factory() -> AsyncMock:
        session = AsyncMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=session)
        cm.__aexit__ = AsyncMock(return_value=False)
        sessions.append(session)
        return cm

    return factory


def _context(ai: _Ai) -> JobContext:
    sessions: list[AsyncMock] = []
    return JobContext(
        settings=_settings(),
        engine=MagicMock(),
        session_factory=_session_factory(sessions),
        identity=WorkerIdentity(hostname="host", pid=1),
        budget=LlmBudget(max_llm_calls=10),
        ai=ai,
    )


def _patch_services(
    *,
    articles: list[AnalysisArticle],
    label_rows: list[object] | None = None,
    candidates: list[object] | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    analysis = MagicMock()
    analysis.load_for_analysis = AsyncMock(return_value=articles)
    analysis.save_text = AsyncMock()
    analysis.save_embedding = AsyncMock()
    analysis.finalize = AsyncMock()

    labels = MagicMock()
    labels.list_labels = AsyncMock(return_value=label_rows or [])
    labels.upsert_label = AsyncMock()

    families = MagicMock()
    families.recent_candidates = AsyncMock(return_value=candidates or [])
    families.create = AsyncMock(return_value=uuid.uuid4())
    families.add_member = AsyncMock()

    queue = MagicMock()
    queue.claim = AsyncMock(
        return_value=[SimpleNamespace(id=article.id) for article in articles]
    )
    queue.fail_id = AsyncMock(return_value=IngestStatus.NEW)
    queue.release = AsyncMock()
    return analysis, labels, families, queue


def _run(
    stage: AnalyzeStage,
    ctx: JobContext,
    *,
    analysis: MagicMock,
    labels: MagicMock,
    families: MagicMock,
    queue: MagicMock,
) -> dict[str, int]:
    with (
        patch(
            "hermes_worker.jobs.stages.analyze.ArticleQueue",
            return_value=queue,
        ),
        patch(
            "hermes_worker.jobs.stages.analyze.ArticleAnalysisService",
            return_value=analysis,
        ),
        patch(
            "hermes_worker.jobs.stages.analyze.ArticleLabelService",
            return_value=labels,
        ),
        patch(
            "hermes_worker.jobs.stages.analyze.ArticleFamilyService",
            return_value=families,
        ),
    ):
        return asyncio.run(stage.run(ctx)).counters


def test_analyze_accepts_event_and_creates_family() -> None:
    article = _article()
    ai = _Ai(ArticleLabelBatchResponse(labels=[_label()]))
    ctx = _context(ai)
    analysis, labels, families, queue = _patch_services(articles=[article])

    stats = _run(
        AnalyzeStage(fetcher=_Fetcher()),
        ctx,
        analysis=analysis,
        labels=labels,
        families=families,
        queue=queue,
    )

    assert stats["claimed"] == 1
    assert stats["loaded"] == 1
    assert stats["fetch_skipped"] == 1
    assert stats["text_feed_summary"] == 1
    assert stats["labels_new"] == 1
    assert stats["label_calls"] == 1
    assert stats["embedded"] == 1
    assert stats["families_created"] == 1
    assert ai.llm.input_types == ["passage"]

    analysis.save_text.assert_awaited_once()
    save_text_kwargs = analysis.save_text.await_args.kwargs
    assert save_text_kwargs["body_source"] == ArticleBodySource.FEED_SUMMARY

    labels.upsert_label.assert_awaited_once()
    assert labels.upsert_label.await_args.args[1] == PROMPT_VERSION

    analysis.save_embedding.assert_awaited_once()
    assert analysis.save_embedding.await_args.kwargs["model"] == "test/embed-model"

    families.create.assert_awaited_once()
    analysis.finalize.assert_awaited_once()
    assert analysis.finalize.await_args.kwargs["status"] == IngestStatus.LABELED
    assert len(ai.llm.calls) == 1


def test_analyze_persists_rejected_label_without_embedding() -> None:
    article = _article()
    ai = _Ai(
        ArticleLabelBatchResponse(
            labels=[
                _label(
                    is_event=False,
                    article_type=ArticleType.OPINION,
                    specificity=1,
                    reject_reason="opinion column",
                )
            ]
        )
    )
    ctx = _context(ai)
    analysis, labels, families, queue = _patch_services(articles=[article])

    stats = _run(
        AnalyzeStage(fetcher=_Fetcher()),
        ctx,
        analysis=analysis,
        labels=labels,
        families=families,
        queue=queue,
    )

    assert stats["rejected_label"] == 1
    assert "embedded" not in stats
    labels.upsert_label.assert_awaited_once()
    families.create.assert_not_awaited()
    analysis.save_embedding.assert_not_awaited()
    analysis.finalize.assert_awaited_once()
    assert analysis.finalize.await_args.kwargs["status"] == IngestStatus.REJECTED
    assert analysis.finalize.await_args.kwargs["reject_reason"].startswith("not_event:")
    assert ai.llm.calls == []


def test_analyze_reuses_matching_label_without_calling_llm() -> None:
    article = _article()
    label_input = build_label_input(index=0, article=article, body=None)
    digest = label_input_hash(label_input)
    row = SimpleNamespace(
        article_id=article.id,
        is_event=True,
        article_type=ArticleType.BREAKING,
        event_time=NOW,
        severity=4,
        scope=EventScope.CITY,
        confidence=0.9,
        fact="A magnitude 6.1 earthquake struck the coastal city.",
        scale_facts={"deaths": 12},
        entities=[{"name": "Coastal City", "kind": "LOCATION"}],
        locations=[{"name": "Coastal City", "country_code": "EX"}],
        category=ArticleCategory.DISASTER,
        event_form=EventForm.INCIDENT,
        specificity=4,
        consequence=4,
        certainty=ArticleCertainty.REPORTED,
        reject_reason=None,
        input_hash=digest,
        evidence_quote="A magnitude 6.1 earthquake struck the coastal city.",
    )
    ai = _Ai(None)
    ctx = _context(ai)
    analysis, labels, families, queue = _patch_services(
        articles=[article],
        label_rows=[row],
    )

    stats = _run(
        AnalyzeStage(fetcher=_Fetcher()),
        ctx,
        analysis=analysis,
        labels=labels,
        families=families,
        queue=queue,
    )

    assert stats["labels_reused"] == 1
    assert "label_calls" not in stats
    assert ctx.budget.used_llm_calls == 0
    assert ai.labels.calls == []
    labels.upsert_label.assert_awaited_once()
    analysis.finalize.assert_awaited_once()
    assert analysis.finalize.await_args.kwargs["status"] == IngestStatus.LABELED


def test_analyze_requeues_when_embedding_is_unavailable() -> None:
    article = _article()

    ai = _Ai(
        ArticleLabelBatchResponse(labels=[_label()]),
        embedding_available=False,
    )
    ctx = _context(ai)
    analysis, labels, families, queue = _patch_services(articles=[article])

    stats = _run(
        AnalyzeStage(fetcher=_Fetcher()),
        ctx,
        analysis=analysis,
        labels=labels,
        families=families,
        queue=queue,
    )

    assert stats["embed_failed"] == 1
    assert stats["embed_retry"] == 1
    families.create.assert_not_awaited()
    analysis.finalize.assert_awaited_once()
    assert analysis.finalize.await_args.kwargs["status"] == IngestStatus.NEW
    assert analysis.finalize.await_args.kwargs["error"] == "embedding unavailable"


def test_analyze_marks_terminal_after_max_attempts() -> None:
    article = _article(attempt_count=5)

    ai = _Ai(
        ArticleLabelBatchResponse(labels=[_label()]),
        embedding_available=False,
    )
    ctx = _context(ai)
    analysis, labels, families, queue = _patch_services(articles=[article])

    stats = _run(
        AnalyzeStage(fetcher=_Fetcher()),
        ctx,
        analysis=analysis,
        labels=labels,
        families=families,
        queue=queue,
    )

    assert stats["embed_terminal"] == 1
    assert analysis.finalize.await_args.kwargs["status"] == IngestStatus.FAILED


def test_analyze_skips_when_budget_is_empty() -> None:
    article = _article()
    ai = _Ai(ArticleLabelBatchResponse(labels=[_label()]))
    ctx = _context(ai)
    ctx.budget = LlmBudget(max_llm_calls=0)
    analysis, labels, families, queue = _patch_services(articles=[article])

    stats = _run(
        AnalyzeStage(fetcher=_Fetcher()),
        ctx,
        analysis=analysis,
        labels=labels,
        families=families,
        queue=queue,
    )

    assert stats == {"budget_empty": 1}
    queue.claim.assert_not_awaited()


def test_analyze_adds_member_to_existing_family() -> None:
    family_id = uuid.uuid4()
    article = _article(family_id=family_id)
    ai = _Ai(ArticleLabelBatchResponse(labels=[_label()]))
    ctx = _context(ai)
    analysis, labels, families, queue = _patch_services(articles=[article])

    stats = _run(
        AnalyzeStage(fetcher=_Fetcher()),
        ctx,
        analysis=analysis,
        labels=labels,
        families=families,
        queue=queue,
    )

    assert stats["family_existing"] == 1
    families.add_member.assert_not_awaited()
    families.create.assert_not_awaited()
    analysis.finalize.assert_awaited_once()
    assert analysis.finalize.await_args.kwargs["status"] == IngestStatus.LABELED

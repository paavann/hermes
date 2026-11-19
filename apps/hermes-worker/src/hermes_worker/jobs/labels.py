from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from hermes_ai.models.labels import ArticleLabelExtraction, LabelArticleInput
from hermes_db.enums import (
    ArticleBodySource,
    ArticleCategory,
    ArticleCertainty,
    ArticleType,
    EventForm,
    EventScope,
    RejectStage,
    SourceFetchPolicy,
)
from hermes_db.models.article_label import ArticleLabel
from hermes_db.services import AnalysisArticle
from hermes_db.utils.datetime import ensure_utc
from hermes_worker.jobs.fetch import FetchResult
from hermes_worker.jobs.fingerprints import sha256_hex, simhash_hex


MIN_SPECIFICITY = 3
MIN_POLICY_ACTION_SPECIFICITY = 4
REJECTED_ARTICLE_TYPES = frozenset(
    {
        ArticleType.ANALYSIS,
        ArticleType.FEATURE,
        ArticleType.LISTICLE,
        ArticleType.OPINION,
    }
)
MAX_GATE_REASON_CHARS = 300


@dataclass(frozen=True, slots=True)
class LabelPayload:
    """Database-ready label implementing ``hermes_db.protocols.ArticleLabelData``."""

    is_event: bool
    article_type: ArticleType
    event_time: datetime | None
    severity: int | None
    scope: EventScope | None
    confidence: float | None
    fact: str | None
    scale_facts: dict[str, object]
    entities: list[dict[str, object]]
    locations: list[dict[str, object]]
    category: ArticleCategory | None
    event_form: EventForm | None
    specificity: int | None
    consequence: int | None
    certainty: ArticleCertainty | None
    reject_reason: str | None
    input_hash: str | None
    evidence_quote: str | None


@dataclass(frozen=True, slots=True)
class GateDecision:
    rejected: bool
    stage: RejectStage | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SelectedText:
    body_source: ArticleBodySource | None
    text: str
    input_quality: float
    word_count: int
    http_status: int | None


def build_label_input(
    *,
    index: int,
    article: AnalysisArticle,
    body: str | None,
) -> LabelArticleInput:
    return LabelArticleInput(
        index=index,
        title=article.title,
        source=article.source_name or "unknown",
        published_at=(
            article.published_at.isoformat() if article.published_at else None
        ),
        language=article.language,
        summary=article.feed_summary,
        body=body,
    )


def label_input_hash(label_input: LabelArticleInput) -> str:
    canonical = json.dumps(
        [
            label_input.title,
            label_input.source,
            label_input.published_at,
            label_input.language,
            label_input.summary,
            label_input.body,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256_hex(canonical)


def select_text(article: AnalysisArticle, fetched: FetchResult | None) -> SelectedText:
    """Choose body text or fall back to the feed summary.

    Source policy is authoritative: ``SUMMARY_ONLY`` and paywalled sources
    never use a fetched body, even if one was requested by mistake.
    """
    http_status = fetched.http_status if fetched is not None else None
    if (
        article.fetch_policy == SourceFetchPolicy.FULL_TEXT
        and not article.paywall
        and fetched is not None
        and fetched.ok
        and fetched.text
    ):
        text = fetched.text
        quality = min(1.0, 0.7 + min(len(text), 3000) / 10_000)
        return SelectedText(
            body_source=ArticleBodySource.FULL_TEXT,
            text=text,
            input_quality=quality,
            word_count=len(text.split()),
            http_status=http_status,
        )

    summary = " ".join((article.feed_summary or "").split())
    if summary:
        quality = min(0.6, 0.25 + len(summary) / 2000)
        return SelectedText(
            body_source=ArticleBodySource.FEED_SUMMARY,
            text=summary,
            input_quality=quality,
            word_count=len(summary.split()),
            http_status=http_status,
        )

    return SelectedText(
        body_source=None,
        text="",
        input_quality=0.1,
        word_count=0,
        http_status=http_status,
    )


def to_label_payload(
    label: ArticleLabelExtraction,
    *,
    input_hash: str,
) -> LabelPayload:
    scale_facts: dict[str, object] = {}
    for key, value in label.scale_facts.items():
        scale_facts[key] = value

    entities: list[dict[str, object]] = [
        {"name": entity.name, "kind": entity.kind.value}
        for entity in label.entities
    ]
    locations: list[dict[str, object]] = [
        {"name": location.name, "country_code": location.country_code}
        for location in label.locations
    ]
    return LabelPayload(
        is_event=label.is_event,
        article_type=ArticleType(label.article_type.value),
        event_time=(
            ensure_utc(label.event_time) if label.event_time is not None else None
        ),
        severity=label.severity,
        scope=EventScope(label.scope.value),
        confidence=label.confidence,
        fact=label.fact,
        scale_facts=scale_facts,
        entities=entities,
        locations=locations,
        category=ArticleCategory(label.category.value),
        event_form=(
            EventForm(label.event_form.value)
            if label.event_form is not None
            else None
        ),
        specificity=label.specificity,
        consequence=label.consequence,
        certainty=(
            ArticleCertainty(label.certainty.value)
            if label.certainty is not None
            else None
        ),
        reject_reason=label.reject_reason,
        input_hash=input_hash,
        evidence_quote=label.evidence_quote,
    )


def payload_from_row(row: ArticleLabel) -> LabelPayload:
    """Rebuild a payload from a persisted label for cost-free retries."""
    return LabelPayload(
        is_event=row.is_event,
        article_type=row.article_type,
        event_time=row.event_time,
        severity=row.severity,
        scope=row.scope,
        confidence=row.confidence,
        fact=row.fact,
        scale_facts=dict(row.scale_facts),
        entities=list(row.entities),
        locations=list(row.locations),
        category=row.category,
        event_form=row.event_form,
        specificity=row.specificity,
        consequence=row.consequence,
        certainty=row.certainty,
        reject_reason=row.reject_reason,
        input_hash=row.input_hash,
        evidence_quote=row.evidence_quote,
    )


def evaluate_gate(label: LabelPayload) -> GateDecision:
    """Apply the deterministic reject policy.

    Labels are still persisted for rejected articles so the decision can be
    audited and scored later.
    """
    if not label.is_event:
        reason = "not_event"
        if label.reject_reason:
            reason = f"{reason}: {label.reject_reason}"
        return GateDecision(
            rejected=True,
            stage=RejectStage.LABEL,
            reason=reason[:MAX_GATE_REASON_CHARS],
        )

    if not label.fact:
        return GateDecision(
            rejected=True,
            stage=RejectStage.LABEL,
            reason="missing_fact",
        )

    if label.article_type in REJECTED_ARTICLE_TYPES:
        return GateDecision(
            rejected=True,
            stage=RejectStage.GATE,
            reason=f"article_type_{label.article_type.value.lower()}",
        )

    specificity = label.specificity or 0
    if specificity < MIN_SPECIFICITY:
        return GateDecision(
            rejected=True,
            stage=RejectStage.GATE,
            reason=f"low_specificity_{specificity}",
        )

    if (
        label.event_form == EventForm.POLICY_ACTION
        and specificity < MIN_POLICY_ACTION_SPECIFICITY
    ):
        return GateDecision(
            rejected=True,
            stage=RejectStage.GATE,
            reason=f"policy_action_low_specificity_{specificity}",
        )

    return GateDecision(rejected=False)


def build_text_hashes(
    *,
    title: str,
    text: str,
) -> tuple[str | None, str | None]:
    return simhash_hex(title), simhash_hex(text) if text else None


def build_embedding_text(label: LabelPayload, *, title: str) -> str:
    parts = [title, label.fact or ""]
    parts.extend(
        str(entity.get("name", ""))
        for entity in label.entities
        if entity.get("name")
    )
    parts.extend(
        str(location.get("name", ""))
        for location in label.locations[:1]
        if location.get("name")
    )
    return "\n".join(part for part in parts if part)


def embedding_input_hash(text: str) -> str:
    return sha256_hex(text)

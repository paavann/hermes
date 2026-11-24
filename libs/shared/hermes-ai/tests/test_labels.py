import asyncio
import json
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from hermes_ai.extractors.labels import (
    MAX_BODY_CHARS,
    MAX_QUOTE_CHARS,
    LabelExtractor,
    build_batch_payload,
    validate_evidence_quote,
)
from hermes_ai.models.labels import (
    ArticleLabelBatchResponse,
    ArticleLabelExtraction,
    LabelArticleInput,
)


def _label(**overrides: object) -> ArticleLabelExtraction:
    base = {
        "index": 0,
        "is_event": True,
        "article_type": "BREAKING",
        "event_form": "INCIDENT",
        "category": "DISASTER",
        "specificity": 5,
        "consequence": 4,
        "certainty": "REPORTED",
        "fact": "An earthquake struck the coast on Tuesday.",
        "event_time": datetime(2026, 11, 18, 9, 0, tzinfo=UTC),
        "locations": [{"name": "Coastal City", "country_code": "ex"}],
        "entities": [{"name": "Coastal City", "kind": "location"}],
        "scale_facts": {"deaths": 12, "magnitude": 6.1},
        "severity": 4,
        "scope": "city",
        "confidence": 0.9,
        "evidence_quote": "An earthquake struck the coast on Tuesday.",
        "reject_reason": None,
    }
    base.update(overrides)
    return ArticleLabelExtraction(**base)


def test_label_normalizes_enum_casing_and_country_code() -> None:
    label = _label()

    assert label.article_type.value == "BREAKING"
    assert label.event_form is not None
    assert label.event_form.value == "INCIDENT"
    assert label.category.value == "DISASTER"
    assert label.certainty is not None
    assert label.certainty.value == "REPORTED"
    assert label.scope.value == "CITY"
    assert label.locations[0].country_code == "EX"
    assert label.entities[0].kind.value == "LOCATION"


def test_label_treats_null_strings_as_missing_optional_enums() -> None:
    label = _label(event_form="NULL", certainty="none")

    assert label.event_form is None
    assert label.certainty is None


def test_label_rejects_invalid_country_code() -> None:
    label = _label(locations=[{"name": "Somewhere", "country_code": "USA"}])

    assert label.locations[0].country_code is None


def test_label_rejects_specificity_outside_range() -> None:
    with pytest.raises(ValidationError):
        _label(specificity=6)


def test_label_rejects_too_many_locations() -> None:
    with pytest.raises(ValidationError):
        _label(
            locations=[
                {"name": "One"},
                {"name": "Two"},
                {"name": "Three"},
                {"name": "Four"},
            ]
        )


def test_batch_response_rejects_duplicate_indexes() -> None:
    with pytest.raises(ValidationError):
        ArticleLabelBatchResponse(labels=[_label(index=0), _label(index=0)])


def test_label_article_input_quote_source_combines_parts() -> None:
    item = LabelArticleInput(
        index=0,
        title="Headline",
        source="Example",
        summary="Summary.",
        body="Body.",
    )

    assert item.quote_source == "Headline Summary. Body."
    assert LabelArticleInput(
        index=0,
        title="Headline",
        source="Example",
    ).quote_source == "Headline"


def test_validate_evidence_quote_accepts_whitespace_normalized_span() -> None:
    source = "Rescue teams   searched collapsed buildings\non Tuesday."

    assert (
        validate_evidence_quote("Rescue teams searched collapsed buildings", source)
        == "Rescue teams searched collapsed buildings"
    )


def test_validate_evidence_quote_drops_fabricated_span() -> None:
    source = "Rescue teams searched collapsed buildings on Tuesday."

    assert validate_evidence_quote("The president declared a holiday", source) is None
    assert validate_evidence_quote(None, source) is None
    assert validate_evidence_quote("   ", source) is None


def test_validate_evidence_quote_truncates_to_limit() -> None:
    source = "word " * 200
    quote = "word " * 200

    validated = validate_evidence_quote(quote, source)

    assert validated is not None
    assert len(validated) == MAX_QUOTE_CHARS


def test_build_batch_payload_truncates_and_omits_unknown_fields() -> None:
    item = LabelArticleInput(
        index=3,
        title="  Headline   with\nwhitespace  ",
        source="Example",
        summary="Summary.",
        body="x" * (MAX_BODY_CHARS + 100),
    )

    payload = json.loads(build_batch_payload([item]))

    assert len(payload) == 1
    entry = payload[0]
    assert entry["index"] == 3
    assert entry["title"] == "Headline with whitespace"
    assert len(entry["body"]) == MAX_BODY_CHARS
    assert "latitude" not in entry
    assert "longitude" not in entry


class _FakeLlm:
    def __init__(self, response: ArticleLabelBatchResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def model_for(self, task: str) -> str:
        assert task == "label"
        return "test/label-model"

    async def complete_json(self, **kwargs: object) -> ArticleLabelBatchResponse:
        self.calls.append(kwargs)
        return self.response


def test_extractor_drops_unknown_indexes_and_validates_quotes() -> None:
    async def _test() -> None:
        response = ArticleLabelBatchResponse(
            labels=[
                _label(
                    index=0,
                    evidence_quote="Rescue teams searched collapsed buildings",
                ),
                _label(index=99),
            ]
        )
        llm = _FakeLlm(response)
        extractor = LabelExtractor(llm)

        result = await extractor.label(
            [
                LabelArticleInput(
                    index=0,
                    title="Quake",
                    source="Example",
                    summary="Rescue teams searched collapsed buildings on Tuesday.",
                )
            ]
        )

        assert result is not None
        assert [label.index for label in result.labels] == [0]
        assert result.labels[0].evidence_quote == (
            "Rescue teams searched collapsed buildings"
        )
        assert extractor.prompt_version == "label-v2"
        assert extractor.model_name == "test/label-model"
        assert len(llm.calls) == 1

    asyncio.run(_test())


def test_extractor_returns_empty_response_for_empty_input() -> None:
    async def _test() -> None:
        llm = _FakeLlm(ArticleLabelBatchResponse(labels=[]))
        extractor = LabelExtractor(llm)

        result = await extractor.label([])

        assert result is not None
        assert result.labels == []
        assert llm.calls == []

    asyncio.run(_test())


def test_batch_payload_preserves_order_and_indexes() -> None:
    items: Sequence[LabelArticleInput] = [
        LabelArticleInput(index=0, title="Zero", source="A"),
        LabelArticleInput(index=1, title="One", source="B"),
    ]

    payload = json.loads(build_batch_payload(items))

    assert [entry["index"] for entry in payload] == [0, 1]

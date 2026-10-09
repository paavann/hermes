"""Unit tests for hermes_ai foundation modules."""

from hermes_ai.core.config import AiConfig
from hermes_ai.core.constants import (
    ARTICLE_BATCH_SIZE,
    DEFAULT_CATEGORY_COLOR,
    PREDEFINED_CATEGORIES,
)
from hermes_ai.models import (
    ArticleInput,
    ExtractedEvent,
    ExtractionResponse,
    TlEdgeExtraction,
    TlExtractionResponse,
    TlNodeExtraction,
    TlSearchQuery,
)
from hermes_ai.utils.coercion import coerce_to_str
from hermes_ai.utils.prompts import (
    ARTICLE_SYSTEM_PROMPT,
    TL_SYSTEM_PROMPT,
    TL_TRIAGE_SYSTEM_PROMPT,
)


def test_coerce_to_str() -> None:
    assert coerce_to_str("simple text") == "simple text"
    assert coerce_to_str({"en": "English text"}) == "English text"
    assert coerce_to_str({"summary": "Summary text"}) == "Summary text"
    assert coerce_to_str(["part1", "part2"]) == "part1 part2"
    assert coerce_to_str(["part1", None, "   ", "part2"]) == "part1 part2"
    assert coerce_to_str(None) == ""
    assert coerce_to_str(True) == ""
    assert coerce_to_str(False) == ""
    assert coerce_to_str(42) == "42"


def test_extracted_event_coercion() -> None:
    event = ExtractedEvent(
        article_index=0,
        has_location=True,
        location_name={"en": "Tokyo, Japan"},
        country_code="JP",
        headline={"en": "Tokyo Summit Concludes"},
        summary="Leaders met in Tokyo.",
        category="POLITICS",
    )
    assert event.location_name == "Tokyo, Japan"
    assert event.headline == "Tokyo Summit Concludes"
    assert event.category == "POLITICS"


def test_article_input_and_extraction_response() -> None:
    article = ArticleInput(title="Test", content="Content")
    assert article.title == "Test"

    event = ExtractedEvent(
        article_index=0,
        has_location=False,
        headline="No location",
        summary="Summary",
        category="ECONOMY",
    )
    response = ExtractionResponse(events=[event])
    assert len(response.events) == 1


def test_timeline_models_coercion() -> None:
    node = TlNodeExtraction(
        date="2024-01-01",
        headline={"en": "Treaty Signed"},
        location_name={"en": "Geneva, Switzerland"},
        summary="The treaty entered into force.",
    )
    assert node.headline == "Treaty Signed"
    assert node.location_name == "Geneva, Switzerland"

    edge = TlEdgeExtraction(
        source_index=0,
        target_index=1,
        relationship={"en": "led to"},
    )
    assert edge.relationship == "led to"

    triage = TlSearchQuery(
        is_tl_worthy=True,
        wiki_search_query="Treaty of Geneva",
    )
    assert triage.is_tl_worthy is True
    assert triage.wiki_search_query == "Treaty of Geneva"

    tl_response = TlExtractionResponse(
        tl_summary={"en": "Historical overview."},
        nodes=[node],
        edges=[edge],
    )
    assert tl_response.tl_summary == "Historical overview."


def test_ai_config_defaults() -> None:
    cfg = AiConfig(primary_model="mistral-large", primary_api_key="secret-key")
    assert cfg.primary_model == "mistral-large"
    assert cfg.fallback_model is None
    assert cfg.num_retries == 2
    assert cfg.cooldown_time == 180
    assert cfg.retry_after is True


def test_constants_and_prompts() -> None:
    assert "CONFLICT" in PREDEFINED_CATEGORIES
    assert DEFAULT_CATEGORY_COLOR == "#6B7280"
    assert ARTICLE_BATCH_SIZE == 10
    assert "news analyst" in ARTICLE_SYSTEM_PROMPT
    assert "geopolitical historian" in TL_SYSTEM_PROMPT
    assert "geopolitical researcher" in TL_TRIAGE_SYSTEM_PROMPT

"""Unit tests for hermes_ai foundation modules."""

import pytest

from hermes_ai.core.config import AiConfig, ModelRoute, ModelTarget
from hermes_ai.core.constants import (
    DEFAULT_CATEGORY_COLOR,
    PREDEFINED_CATEGORIES,
)
from hermes_ai.exceptions import ConfigurationError
from hermes_ai.models import (
    TlEdgeExtraction,
    TlExtractionResponse,
    TlNodeExtraction,
    TlSearchQuery,
)
from hermes_ai.utils.coercion import coerce_to_str
from hermes_ai.utils.prompts import (
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
    route = ModelRoute(primary=ModelTarget(model="mistral-large", api_key="secret-key"))
    cfg = AiConfig(routes={"extractor": route})
    assert cfg.routes["extractor"].primary.model == "mistral-large"
    assert cfg.routes["extractor"].primary.api_key == "secret-key"
    assert len(cfg.routes["extractor"].fallbacks) == 0
    assert cfg.num_retries == 2
    assert cfg.cooldown_time == 180
    assert cfg.retry_after is True
    assert cfg.has_chat is False
    assert cfg.has_plan is False
    assert cfg.has_embed is False
    assert cfg.tavily_api_key is None
    assert cfg.chat_stream_include_usage is True
    assert cfg.web_timeout_seconds == 8.0
    assert cfg.chat_max_output_tokens == 1200
    assert cfg.langfuse_mask_content is True


def test_ai_config_routes() -> None:
    cfg = AiConfig(
        routes={
            "extractor": ModelRoute(
                primary=ModelTarget(model="mistral-large", api_key="secret-key"),
                fallbacks=(
                    ModelTarget(model="fallback-large", api_key="fallback-key"),
                ),
            ),
            "chat": ModelRoute(
                primary=ModelTarget(
                    model="provider/chat-model", api_key="chat-key", rpm=42
                ),
            ),
            "plan": ModelRoute(
                primary=ModelTarget(
                    model="provider/plan-model", api_key="plan-key", rpm=42
                ),
            ),
            "embed": ModelRoute(
                primary=ModelTarget(
                    model="nvidia_nim/nemotron", api_key="embed-key", rpm=120
                ),
                fallbacks=(
                    ModelTarget(
                        model="self_hosted/nemotron", api_key="alt-key", rpm=120
                    ),
                ),
            ),
        }
    )
    assert cfg.has_chat is True
    assert cfg.has_plan is True
    assert cfg.has_embed is True
    assert cfg.routes["embed"].primary.model == "nvidia_nim/nemotron"
    assert cfg.routes["embed"].primary.api_key == "embed-key"
    assert cfg.routes["embed"].primary.rpm == 120
    assert len(cfg.routes["extractor"].fallbacks) == 1
    assert cfg.routes["extractor"].fallbacks[0].model == "fallback-large"
    assert cfg.routes["extractor"].fallbacks[0].api_key == "fallback-key"


def test_ai_config_without_extractor_succeeds() -> None:
    cfg = AiConfig(
        routes={
            "chat": ModelRoute(
                primary=ModelTarget(model="provider/chat", api_key="key")
            )
        }
    )
    assert cfg.has_chat is True
    assert cfg.has_plan is False
    assert cfg.has_embed is False
    assert "extractor" not in cfg.routes


def test_ai_config_rejects_empty_routes() -> None:
    with pytest.raises(ConfigurationError, match="routes are required in AiConfig"):
        AiConfig(routes={})


def test_ai_config_rejects_missing_primary() -> None:
    with pytest.raises(
        ConfigurationError,
        match="extractor primary model and api key are required",
    ):
        AiConfig(
            routes={
                "extractor": ModelRoute(
                    primary=ModelTarget(model="", api_key="secret-key")
                )
            }
        )


def test_ai_config_rejects_invalid_fallback() -> None:
    with pytest.raises(
        ConfigurationError,
        match="extractor fallback #1 model and api key are required",
    ):
        AiConfig(
            routes={
                "extractor": ModelRoute(
                    primary=ModelTarget(model="mistral-large", api_key="key"),
                    fallbacks=(ModelTarget(model="", api_key="fallback-key"),),
                )
            }
        )

    with pytest.raises(
        ConfigurationError, match="chat primary model and api key are required"
    ):
        AiConfig(
            routes={
                "extractor": ModelRoute(
                    primary=ModelTarget(model="mistral-large", api_key="key")
                ),
                "chat": ModelRoute(primary=ModelTarget(model="", api_key="chat-key")),
            }
        )


def test_constants_and_prompts() -> None:
    assert "CONFLICT" in PREDEFINED_CATEGORIES
    assert DEFAULT_CATEGORY_COLOR == "#6B7280"
    assert "geopolitical historian" in TL_SYSTEM_PROMPT
    assert "geopolitical researcher" in TL_TRIAGE_SYSTEM_PROMPT

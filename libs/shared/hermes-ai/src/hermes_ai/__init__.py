"""Hermes AI: Shared AI and LLM abstraction library."""

from hermes_ai.core.config import AiConfig
from hermes_ai.core.constants import (
    ARTICLE_BATCH_SIZE,
    DEFAULT_CATEGORY_COLOR,
    PREDEFINED_CATEGORIES,
)
from hermes_ai.models.events import (
    ArticleInput,
    ExtractedEvent,
    ExtractionResponse,
)
from hermes_ai.models.tl import (
    TlEdgeExtraction,
    TlExtractionResponse,
    tlNodeExtraction,
    tlSearchQuery,
)
from hermes_ai.utils.coercion import coerce_to_str
from hermes_ai.utils.prompts import (
    ARTICLE_SYSTEM_PROMPT,
    TL_SYSTEM_PROMPT,
    TL_TRIAGE_SYSTEM_PROMPT,
)


__all__ = [
    "ARTICLE_BATCH_SIZE",
    "ARTICLE_SYSTEM_PROMPT",
    "AiConfig",
    "ArticleInput",
    "DEFAULT_CATEGORY_COLOR",
    "ExtractedEvent",
    "ExtractionResponse",
    "PREDEFINED_CATEGORIES",
    "TL_SYSTEM_PROMPT",
    "TL_TRIAGE_SYSTEM_PROMPT",
    "TlEdgeExtraction",
    "TlExtractionResponse",
    "coerce_to_str",
    "tlNodeExtraction",
    "tlSearchQuery",
]

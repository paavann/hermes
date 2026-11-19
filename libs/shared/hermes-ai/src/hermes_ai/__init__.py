"""Public API exports for the hermes-ai package."""

from hermes_ai.client import HermesAi
from hermes_ai.core.config import AiConfig, ModelRoute, ModelTarget
from hermes_ai.core.constants import (
    DEFAULT_CATEGORY_COLOR,
    PREDEFINED_CATEGORIES,
)
from hermes_ai.exceptions import (
    CircuitBreakerOpenError,
    ConfigurationError,
    GeocodingError,
    HermesAiError,
    ModelExecutionError,
    RateLimitExceededError,
    SchemaValidationError,
)
from hermes_ai.extractors.labels import LabelExtractor
from hermes_ai.extractors.tl import TlExtractor
from hermes_ai.models.labels import (
    ArticleLabelBatchResponse,
    ArticleLabelExtraction,
    LabelArticleInput,
    LabelArticleType,
    LabelCategory,
    LabelCertainty,
    LabelEntity,
    LabelEntityKind,
    LabelEventForm,
    LabelLocation,
    LabelScope,
)
from hermes_ai.models.tl import (
    TlEdgeExtraction,
    TlExtractionResponse,
    TlNodeExtraction,
    TlSearchQuery,
)
from hermes_ai.services.geocoding import (
    GeocodeCacheProtocol,
    GeocodingResult,
    GeocodingService,
    NominatimResilienceManager,
    clean_location_name,
)
from hermes_ai.services.llm import LlmService, LlmUsage
from hermes_ai.utils.coercion import coerce_to_str
from hermes_ai.utils.prompts import (
    ARTICLE_LABEL_PROMPT_VERSION,
    ARTICLE_LABEL_SYSTEM_PROMPT,
    TL_SYSTEM_PROMPT,
    TL_TRIAGE_SYSTEM_PROMPT,
)
from hermes_ai.utils.rate_limiter import TbRateLimiter


__all__ = [
    "AiConfig",
    "ArticleLabelBatchResponse",
    "ArticleLabelExtraction",
    "ARTICLE_LABEL_PROMPT_VERSION",
    "ARTICLE_LABEL_SYSTEM_PROMPT",
    "CircuitBreakerOpenError",
    "ConfigurationError",
    "DEFAULT_CATEGORY_COLOR",
    "GeocodeCacheProtocol",
    "GeocodingError",
    "GeocodingResult",
    "GeocodingService",
    "HermesAi",
    "HermesAiError",
    "LabelArticleInput",
    "LabelArticleType",
    "LabelCategory",
    "LabelCertainty",
    "LabelEntity",
    "LabelEntityKind",
    "LabelEventForm",
    "LabelExtractor",
    "LabelLocation",
    "LabelScope",
    "LlmService",
    "LlmUsage",
    "ModelExecutionError",
    "ModelRoute",
    "ModelTarget",
    "NominatimResilienceManager",
    "PREDEFINED_CATEGORIES",
    "RateLimitExceededError",
    "SchemaValidationError",
    "TL_SYSTEM_PROMPT",
    "TL_TRIAGE_SYSTEM_PROMPT",
    "TbRateLimiter",
    "TlEdgeExtraction",
    "TlExtractionResponse",
    "TlExtractor",
    "TlNodeExtraction",
    "TlSearchQuery",
    "clean_location_name",
    "coerce_to_str",
]

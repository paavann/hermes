import logging
from hermes_ai import (
    AiConfig,
    HermesAi,
    TlEdgeExtraction,
    TlExtractionResponse,
    TlNodeExtraction,
    TlSearchQuery,
)
from hermes_api.core.config import settings


logger = logging.getLogger(__name__)

tlNodeExtraction = TlNodeExtraction
TimelineSearchQuery = TlSearchQuery


class AiService:
    """Service facade delegating AI timeline extraction and context analysis to hermes-ai."""

    def __init__(self) -> None:
        if not settings.LLM_API or not settings.LLM_MODEL:
            logger.error("primary llm api key or model is missing.")
            raise ValueError("LLM_API or LLM_MODEL is missing.")

        tracing = bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)
        if tracing:
            logger.info("langfuse tracing is enabled for ai service.")

        self._client = HermesAi(
            AiConfig(
                primary_model=settings.LLM_MODEL,
                primary_api_key=settings.LLM_API,
                fallback_model=settings.LLM_MODEL_1,
                fallback_api_key=settings.LLM_API_1,
                rpm_limit=settings.RPM_LIMIT,
                embed_model=settings.EMBED_MODEL,
                embed_api_key=settings.EMBED_API,
                embed_rpm_limit=settings.EMBED_RPM_LIMIT,
                tracing_enabled=tracing,
                tracing_tags=["hermes-api", settings.ENV],
                langfuse_public_key=settings.LANGFUSE_PUBLIC_KEY or None,
                langfuse_secret_key=settings.LANGFUSE_SECRET_KEY or None,
                langfuse_host=settings.LANGFUSE_HOST or None,
            )
        )

        logger.info(
            "ai service initialized using hermes-ai. primary=%s, fallback=%s.",
            settings.LLM_MODEL,
            settings.LLM_MODEL_1 or "none",
        )

    @property
    def client(self) -> HermesAi:
        return self._client

    async def extract_tl(
        self, pg_title: str, prose: str
    ) -> TlExtractionResponse | None:
        """Extract a chronological event timeline from Wikipedia prose."""
        return await self._client.timelines.extract(pg_title, prose)

    async def analyze_tl_context(self, headline: str) -> TlSearchQuery | None:
        """Analyze whether an event headline warrants historical timeline synthesis."""
        return await self._client.timelines.analyze(headline)


__all__ = [
    "AiService",
    "TimelineSearchQuery",
    "TlEdgeExtraction",
    "TlExtractionResponse",
    "TlNodeExtraction",
    "TlSearchQuery",
    "tlNodeExtraction",
]

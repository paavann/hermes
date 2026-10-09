import logging
from hermes_ai import (
    AiConfig,
    ArticleInput,
    ExtractedEvent,
    GeocodingService,
    HermesAiClient,
)
from hermes_worker.core.config import settings


logger = logging.getLogger(__name__)


class AiService:
    def __init__(self) -> None:
        config = AiConfig(
            primary_model=settings.LLM_MODEL,
            primary_api_key=settings.LLM_API,
            fallback_model=settings.LLM_MODEL_1,
            fallback_api_key=settings.LLM_API_1,
            embed_model=settings.EMBED_MODEL,
            embed_api_key=settings.EMBED_API,
            num_retries=2,
            cooldown_time=180,
            retry_after=True,
            rpm_limit=settings.RPM_LIMIT,
            embed_rpm_limit=settings.EMBED_RPM_LIMIT,
        )
        self._client = HermesAiClient(config)
        self._router = self._client.router
        self.router = self._client.router


    async def get_metadata(
        self,
        articles: list[ArticleInput],
        existing_events: list[dict[str, str]],
        geocoding_svc: GeocodingService | None = None,
    ) -> list[ExtractedEvent | None]:
        return await self._client.extract_events(
            articles=articles,
            existing_events=existing_events,
            geocoding_svc=geocoding_svc,
        )


    async def gen_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        return await self._client.gen_embeddings(texts)

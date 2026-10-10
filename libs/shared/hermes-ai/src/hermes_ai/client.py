import logging

from litellm.router import Router
from pydantic import BaseModel

from hermes_ai.core.config import AiConfig
from hermes_ai.extractors.events import EventExtractor
from hermes_ai.extractors.tl import TlExtractor
from hermes_ai.models.events import ArticleInput, ExtractedEvent
from hermes_ai.models.tl import TlExtractionResponse, TlSearchQuery
from hermes_ai.services.geocoding import GeocodingService
from hermes_ai.services.llm import LlmService
from hermes_ai.utils.rate_limiter import TbRateLimiter


logger = logging.getLogger(__name__)


class HermesAiClient:
    """Unified client orchestrating LLM inference, extraction, and geocoding."""

    def __init__(self, config: AiConfig) -> None:
        self._config = config
        self._llm = LlmService(config)
        self._events_extractor = EventExtractor(self)
        self._tl_extractor = TlExtractor(self)

        logger.info("hermes ai client initialized.")


    @property
    def llm(self) -> LlmService:
        return self._llm


    @property
    def router(self) -> Router:
        return self._llm.router


    @property
    def _router(self) -> Router:
        return self._llm.router


    @property
    def rate_limiter(self) -> TbRateLimiter | None:
        return self._llm.rate_limiter


    @property
    def embed_rate_limiter(self) -> TbRateLimiter | None:
        return self._llm.embed_rate_limiter


    async def call_llm[T: BaseModel](
        self,
        sys_prompt: str,
        user_prompt: str,
        res_model: type[T],
        schema_name: str,
    ) -> T | None:
        return await self._llm.call_llm(
            sys_prompt=sys_prompt,
            user_prompt=user_prompt,
            res_model=res_model,
            schema_name=schema_name,
        )


    async def gen_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        return await self._llm.gen_embeddings(texts)


    async def extract_events(
        self,
        articles: list[ArticleInput],
        existing_events: list[dict[str, str]] | None = None,
        geocoding_svc: GeocodingService | None = None,
    ) -> list[ExtractedEvent | None]:
        return await self._events_extractor.extract_events(
            articles, existing_events, geocoding_svc
        )


    async def extract_tl(
        self,
        pg_title: str,
        prose: str,
        geocoding_svc: GeocodingService | None = None,
    ) -> TlExtractionResponse | None:
        return await self._tl_extractor.extract_tl(pg_title, prose, geocoding_svc)


    async def analyze_tl_context(self, headline: str) -> TlSearchQuery | None:
        return await self._tl_extractor.analyze_tl_context(headline)

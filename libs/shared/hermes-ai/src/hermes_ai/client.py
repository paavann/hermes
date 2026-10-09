import logging

import litellm
from litellm.router import Router
from litellm.types.router import DeploymentTypedDict
from pydantic import BaseModel

from hermes_ai.core.config import AiConfig
from hermes_ai.extractors.events import EventExtractor
from hermes_ai.extractors.tl import TlExtractor
from hermes_ai.models.events import ArticleInput, ExtractedEvent
from hermes_ai.models.tl import TlExtractionResponse, TlSearchQuery
from hermes_ai.services.geocoding import GeocodingService
from hermes_ai.utils.rate_limiter import TbRateLimiter


logger = logging.getLogger(__name__)


class HermesAiClient:
    def __init__(self, config: AiConfig) -> None:
        self._config = config
        if not config.primary_api_key or not config.primary_model:
            logger.error("primary llm api key or model is missing.")
            raise ValueError("primary_api_key and primary_model are required.")

        model_list: list[DeploymentTypedDict] = [
            {
                "model_name": "primary-extractor",
                "litellm_params": {
                    "model": config.primary_model,
                    "api_key": config.primary_api_key,
                },
            }
        ]
        fallbacks: list[dict[str, list[str]]] = []
        if config.fallback_model and config.fallback_api_key:
            model_list.append(
                {
                    "model_name": "fallback-extractor",
                    "litellm_params": {
                        "model": config.fallback_model,
                        "api_key": config.fallback_api_key,
                    },
                }
            )
            fallbacks = [{"primary-extractor": ["fallback-extractor"]}]

        self._router = Router(
            model_list=model_list,
            fallbacks=fallbacks,
            num_retries=config.num_retries,
            cooldown_time=config.cooldown_time,
            retry_after=config.retry_after,
        )
        self._events_extractor = EventExtractor(self)
        self._tl_extractor = TlExtractor(self)
        self._rate_limiter = (
            TbRateLimiter(config.rpm_limit) if config.rpm_limit else None
        )
        self._embed_rate_limiter = (
            TbRateLimiter(config.embed_rpm_limit) if config.embed_rpm_limit else None
        )

        logger.info(
            "ai service initialized. primary=%s, fallback=%s via litellm router.",
            config.primary_model,
            config.fallback_model if fallbacks else "none",
        )


    @property
    def router(self) -> Router:
        return self._router

    @property
    def rate_limiter(self) -> TbRateLimiter | None:
        return self._rate_limiter

    @property
    def embed_rate_limiter(self) -> TbRateLimiter | None:
        return self._embed_rate_limiter


    async def call_llm[T: BaseModel] (
        self,
        sys_prompt: str,
        user_prompt: str,
        res_model: type[T],
        schema_name: str,
    ) -> T | None:
        if self._rate_limiter:
            await self._rate_limiter.acquire()
        try:
            res = await self._router.acompletion(
                model="primary-extractor",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": res_model.model_json_schema(),
                    },
                },
            )
            content = res.choices[0].message.content
            if not content:
                logger.warning("llm returned empty content for %s.", schema_name)
                return None
            else:
                return res_model.model_validate_json(content)
        except Exception as exc:
            logger.error("llm call failed for %s: %s.", schema_name, exc)
            return None


    async def gen_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        if not texts:
            return []

        if not self._config.embed_model or not self._config.embed_api_key:
            logger.error("embed api key or model is missing.")
            return [None] * len(texts)

        if self._embed_rate_limiter:
            await self._embed_rate_limiter.acquire()

        try:
            res = await litellm.aembedding(
                model=self._config.embed_model,
                input=texts,
                api_key=self._config.embed_api_key,
                encoding_format="float"
                if self._config.embed_model.startswith("nvidia_nim/")
                else None,
            )
            return [item["embedding"] for item in res.data]
        except Exception as exc:
            logger.error("failed to generate embeddings: %s.", exc)
            return [None] * len(texts)


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

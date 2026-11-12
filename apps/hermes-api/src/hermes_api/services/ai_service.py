import logging
from hermes_ai import (
    AiConfig,
    HermesAi,
    ModelRoute,
    ModelTarget,
)
from hermes_api.core.config import Settings, settings


logger = logging.getLogger(__name__)


def _build_route(
    model: str,
    api_key: str,
    *,
    fallback_model: str | None = None,
    fallback_api_key: str | None = None,
    rpm: int | None = None,
) -> ModelRoute:
    """Build a primary/fallback ``ModelRoute`` from centralized settings."""
    fallbacks: tuple[ModelTarget, ...] = (
        (ModelTarget(model=fallback_model, api_key=fallback_api_key, rpm=rpm),)
        if fallback_model and fallback_api_key
        else ()
    )
    return ModelRoute(
        primary=ModelTarget(model=model, api_key=api_key, rpm=rpm),
        fallbacks=fallbacks,
    )


class AiService:
    def __init__(self, config: Settings = settings) -> None:
        tracing = bool(config.LANGFUSE_PUBLIC_KEY and config.LANGFUSE_SECRET_KEY)
        if tracing:
            logger.info("langfuse tracing is enabled for ai service.")

        routes: dict[str, ModelRoute] = {}
        if config.LLM_MODEL and config.LLM_API:
            routes["extractor"] = _build_route(
                config.LLM_MODEL,
                config.LLM_API,
                fallback_model=config.LLM_MODEL_1,
                fallback_api_key=config.LLM_API_1,
                rpm=config.RPM_LIMIT,
            )

        if config.CHAT_ENABLED:
            chat_model = config.CHAT_MODEL or config.LLM_MODEL
            chat_api_key = config.CHAT_API or config.LLM_API
            if chat_model and chat_api_key:
                plan_model = config.PLAN_MODEL or chat_model
                plan_api_key = config.PLAN_API or chat_api_key
                routes["chat"] = _build_route(
                    chat_model,
                    chat_api_key,
                    fallback_model=config.CHAT_MODEL_1,
                    fallback_api_key=config.CHAT_API_1,
                    rpm=config.CHAT_RPM_LIMIT,
                )
                routes["plan"] = _build_route(
                    plan_model,
                    plan_api_key,
                    fallback_model=config.PLAN_MODEL_1,
                    fallback_api_key=config.PLAN_API_1,
                    rpm=config.CHAT_RPM_LIMIT,
                )

        if config.EMBED_MODEL and config.EMBED_API:
            routes["embed"] = _build_route(
                config.EMBED_MODEL,
                config.EMBED_API,
                fallback_model=config.EMBED_MODEL_1,
                fallback_api_key=config.EMBED_API_1,
                rpm=config.EMBED_RPM_LIMIT,
            )

        if not routes:
            logger.error("primary llm api key or model is missing.")
            raise ValueError("LLM_API or LLM_MODEL is missing.")

        self._client = HermesAi(
            AiConfig(
                routes=routes,
                rpm_limit=config.RPM_LIMIT,
                tracing_enabled=tracing,
                tracing_tags=["hermes-api", config.ENV],
                langfuse_public_key=config.LANGFUSE_PUBLIC_KEY or None,
                langfuse_secret_key=config.LANGFUSE_SECRET_KEY or None,
                langfuse_host=config.LANGFUSE_HOST or None,
                langfuse_mask_content=config.LANGFUSE_MASK_CONTENT,
                chat_stream_include_usage=config.CHAT_STREAM_INCLUDE_USAGE,
                chat_max_output_tokens=config.CHAT_MAX_OUTPUT_TOKENS,
                web_timeout_seconds=config.CHAT_WEB_TIMEOUT_SECONDS,
                tavily_api_key=config.TAVILY_API_KEY or None,
            )
        )
        logger.info("ai service initialized using hermes-ai.")

    @property
    def client(self) -> HermesAi:
        return self._client

    async def aclose(self) -> None:
        await self._client.aclose()


__all__ = ["AiService"]

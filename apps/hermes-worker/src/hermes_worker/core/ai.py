from hermes_ai import AiConfig, HermesAi, ModelRoute, ModelTarget
from hermes_worker.core.config import settings


def create_ai_client() -> HermesAi:
    tracing = bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)

    fallbacks: tuple[ModelTarget, ...] = (
        (
            ModelTarget(
                model=settings.LLM_MODEL_1,
                api_key=settings.LLM_API_1,
                rpm=settings.RPM_LIMIT,
            ),
        )
        if settings.LLM_MODEL_1 and settings.LLM_API_1
        else ()
    )
    routes = {
        "extractor": ModelRoute(
            primary=ModelTarget(
                model=settings.LLM_MODEL,
                api_key=settings.LLM_API,
                rpm=settings.RPM_LIMIT,
            ),
            fallbacks=fallbacks,
        ),
    }
    if settings.EMBED_MODEL and settings.EMBED_API:
        embed_fallbacks: tuple[ModelTarget, ...] = (
            (
                ModelTarget(
                    model=settings.EMBED_MODEL_1,
                    api_key=settings.EMBED_API_1,
                    rpm=settings.EMBED_RPM_LIMIT,
                ),
            )
            if settings.EMBED_MODEL_1 and settings.EMBED_API_1
            else ()
        )
        routes["embed"] = ModelRoute(
            primary=ModelTarget(
                model=settings.EMBED_MODEL,
                api_key=settings.EMBED_API,
                rpm=settings.EMBED_RPM_LIMIT,
            ),
            fallbacks=embed_fallbacks,
        )

    config = AiConfig(
        routes=routes,
        num_retries=2,
        cooldown_time=180,
        retry_after=True,
        rpm_limit=settings.RPM_LIMIT,
        tracing_enabled=tracing,
        tracing_tags=["hermes-worker", settings.ENV],
        langfuse_public_key=settings.LANGFUSE_PUBLIC_KEY or None,
        langfuse_secret_key=settings.LANGFUSE_SECRET_KEY or None,
        langfuse_host=settings.LANGFUSE_HOST or None,
    )

    return HermesAi(config)

from hermes_ai import AiConfig, HermesAi
from hermes_worker.core.config import settings


def create_ai_client() -> HermesAi:
    tracing = bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)

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
        tracing_enabled=tracing,
        tracing_tags=["hermes-worker", settings.ENV],
        langfuse_public_key=settings.LANGFUSE_PUBLIC_KEY or None,
        langfuse_secret_key=settings.LANGFUSE_SECRET_KEY or None,
        langfuse_host=settings.LANGFUSE_HOST or None,
    )

    return HermesAi(config)

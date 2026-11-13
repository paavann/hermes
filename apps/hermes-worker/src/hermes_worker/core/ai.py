from pydantic import SecretStr
from hermes_ai import AiConfig, HermesAi, ModelRoute, ModelTarget
from hermes_worker.core.config import Settings, get_settings


def _to_target(
    model: str | None,
    api_key: SecretStr | None,
    rpm: int,
) -> ModelTarget | None:
    raw_key = api_key.get_secret_value() if api_key else ""
    if not (model and raw_key):
        return None
    return ModelTarget(model=model, api_key=raw_key, rpm=rpm)

def _build_route(
    primary_model: str,
    primary_key: SecretStr,
    fallback_model: str | None,
    fallback_key: SecretStr | None,
    rpm: int,
) -> ModelRoute | None:
    primary = _to_target(primary_model, primary_key, rpm)
    if primary is None:
        return None
    fallback = _to_target(fallback_model, fallback_key, rpm)
    return ModelRoute(
        primary=primary,
        fallbacks=(fallback,) if fallback else (),
    )


def create_ai_client(settings: Settings) -> HermesAi:
    langfuse_secret = settings.LANGFUSE_SECRET_KEY.get_secret_value()
    tracing = bool(settings.LANGFUSE_PUBLIC_KEY and langfuse_secret)

    routes: dict[str, ModelRoute] = {}

    extractor_route = _build_route(
        primary_model=settings.LLM_MODEL,
        primary_key=settings.LLM_API,
        fallback_model=settings.LLM_MODEL_1,
        fallback_key=settings.LLM_API_1,
        rpm=settings.RPM_LIMIT,
    )
    if extractor_route:
        routes["extractor"] = extractor_route

    embed_route = _build_route(
        primary_model=settings.EMBED_MODEL,
        primary_key=settings.EMBED_API,
        fallback_model=settings.EMBED_MODEL_1,
        fallback_key=settings.EMBED_API_1,
        rpm=settings.EMBED_RPM_LIMIT,
    )
    if embed_route:
        routes["embed"] = embed_route

    config = AiConfig(
        routes=routes,
        num_retries=2,
        cooldown_time=180,
        retry_after=True,
        rpm_limit=settings.RPM_LIMIT,
        tracing_enabled=tracing,
        tracing_tags=["hermes-worker", settings.ENV],
        langfuse_public_key=settings.LANGFUSE_PUBLIC_KEY or None,
        langfuse_secret_key=langfuse_secret or None,
        langfuse_host=str(settings.LANGFUSE_HOST),
    )

    return HermesAi(config)

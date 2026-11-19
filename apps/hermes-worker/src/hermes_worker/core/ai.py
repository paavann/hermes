from dataclasses import dataclass
from hermes_ai import AiConfig, HermesAi, ModelRoute, ModelTarget
from pydantic import SecretStr
from hermes_worker.core.config import Settings


@dataclass(frozen=True, slots=True)
class _RouteSpec:
    name: str
    primary_model: str
    primary_key: SecretStr
    fallback_model: str | None
    fallback_key: SecretStr | None
    rpm: int


def _to_target(
    model: str | None,
    api_key: SecretStr | None,
    rpm: int,
) -> ModelTarget | None:
    raw_key = api_key.get_secret_value() if api_key else ""
    if not (model and raw_key):
        return None
    return ModelTarget(model=model, api_key=raw_key, rpm=rpm)


def _resolve_key(override: SecretStr | None, default: SecretStr) -> SecretStr:
    if override is not None and override.get_secret_value():
        return override
    return default


def _build_route(spec: _RouteSpec) -> ModelRoute | None:
    primary = _to_target(spec.primary_model, spec.primary_key, spec.rpm)
    if primary is None:
        return None
    fallback = _to_target(spec.fallback_model, spec.fallback_key, spec.rpm)
    return ModelRoute(
        primary=primary,
        fallbacks=(fallback,) if fallback else (),
    )


def create_ai_client(settings: Settings) -> HermesAi:
    langfuse_secret = settings.LANGFUSE_SECRET_KEY.get_secret_value()
    tracing = bool(settings.LANGFUSE_PUBLIC_KEY and langfuse_secret)

    chat_route_overrides = (
        ("extractor", None, None),
        ("label", settings.LABEL_MODEL, settings.LABEL_API),
        ("adjudicate", settings.ADJUDICATE_MODEL, settings.ADJUDICATE_API),
        ("describe", settings.DESCRIBE_MODEL, settings.DESCRIBE_API),
    )

    specs: list[_RouteSpec] = [
        _RouteSpec(
            name=name,
            primary_model=model_override or settings.LLM_MODEL,
            primary_key=_resolve_key(key_override, settings.LLM_API),
            fallback_model=settings.LLM_MODEL_1,
            fallback_key=settings.LLM_API_1,
            rpm=settings.RPM_LIMIT,
        )
        for name, model_override, key_override in chat_route_overrides
    ]
    specs.append(
        _RouteSpec(
            name="embed",
            primary_model=settings.EMBED_MODEL,
            primary_key=settings.EMBED_API,
            fallback_model=settings.EMBED_MODEL_1,
            fallback_key=settings.EMBED_API_1,
            rpm=settings.EMBED_RPM_LIMIT,
        )
    )

    routes = {
        spec.name: route
        for spec in specs
        if (route := _build_route(spec)) is not None
    }

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

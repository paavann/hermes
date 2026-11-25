from dataclasses import dataclass, field
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
    primary_kwargs: dict[str, object] = field(default_factory=dict)
    fallback_kwargs: dict[str, object] = field(default_factory=dict)
    timeout_seconds: float | None = None


def _to_target(
    model: str | None,
    api_key: SecretStr | None,
    rpm: int,
    *,
    model_kwargs: dict[str, object] | None = None,
    timeout_seconds: float | None = None,
) -> ModelTarget | None:
    raw_key = api_key.get_secret_value() if api_key else ""
    if not (model and raw_key):
        return None
    return ModelTarget(
        model=model,
        api_key=raw_key,
        rpm=rpm,
        model_kwargs=dict(model_kwargs) if model_kwargs else {},
        timeout_seconds=timeout_seconds,
    )


def _resolve_key(override: SecretStr | None, default: SecretStr) -> SecretStr:
    if override is not None and override.get_secret_value():
        return override
    return default


def _build_route(spec: _RouteSpec) -> ModelRoute | None:
    primary = _to_target(
        spec.primary_model,
        spec.primary_key,
        spec.rpm,
        model_kwargs=spec.primary_kwargs,
        timeout_seconds=spec.timeout_seconds,
    )
    if primary is None:
        return None
    fallback = _to_target(
        spec.fallback_model,
        spec.fallback_key,
        spec.rpm,
        model_kwargs=spec.fallback_kwargs,
        timeout_seconds=spec.timeout_seconds,
    )
    return ModelRoute(
        primary=primary,
        fallbacks=(fallback,) if fallback else (),
    )


def create_ai_client(settings: Settings) -> HermesAi:
    langfuse_secret = settings.LANGFUSE_SECRET_KEY.get_secret_value()
    tracing = bool(settings.LANGFUSE_PUBLIC_KEY and langfuse_secret)

    chat_route_overrides = (
        ("extractor", None, None, None),
        (
            "label",
            settings.LABEL_MODEL,
            settings.LABEL_API,
            settings.LABEL_MODEL_KWARGS,
        ),
        (
            "adjudicate",
            settings.ADJUDICATE_MODEL,
            settings.ADJUDICATE_API,
            settings.ADJUDICATE_MODEL_KWARGS,
        ),
        (
            "describe",
            settings.DESCRIBE_MODEL,
            settings.DESCRIBE_API,
            settings.DESCRIBE_MODEL_KWARGS,
        ),
        (
            "thread",
            settings.THREAD_MODEL,
            settings.THREAD_API,
            settings.THREAD_MODEL_KWARGS,
        ),
    )

    specs: list[_RouteSpec] = []
    for name, model_override, key_override, kwargs_override in chat_route_overrides:
        primary_model = model_override or settings.LLM_MODEL
        primary_kwargs = (
            dict(kwargs_override)
            if kwargs_override is not None
            else dict(settings.LLM_MODEL_KWARGS)
        )
        fallback_kwargs = (
            dict(settings.LLM_MODEL_KWARGS)
            if settings.LLM_MODEL_1 == settings.LLM_MODEL
            else {}
        )
        specs.append(
            _RouteSpec(
                name=name,
                primary_model=primary_model,
                primary_key=_resolve_key(key_override, settings.LLM_API),
                fallback_model=settings.LLM_MODEL_1,
                fallback_key=settings.LLM_API_1,
                rpm=settings.RPM_LIMIT,
                primary_kwargs=primary_kwargs,
                fallback_kwargs=fallback_kwargs,
                timeout_seconds=settings.LLM_REQUEST_TIMEOUT_SECONDS,
            )
        )
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
        spec.name: route for spec in specs if (route := _build_route(spec)) is not None
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

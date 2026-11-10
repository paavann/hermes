from __future__ import annotations

from dataclasses import dataclass, field

from hermes_ai.exceptions import ConfigurationError


@dataclass(frozen=True)
class ModelTarget:
    model: str
    api_key: str
    rpm: int | None = None
    tpm: int | None = None


@dataclass(frozen=True)
class ModelRoute:
    primary: ModelTarget
    fallbacks: tuple[ModelTarget, ...] = ()


@dataclass(frozen=True)
class AiConfig:
    routes: dict[str, ModelRoute]
    num_retries: int = 2
    cooldown_time: int = 180
    retry_after: bool = True
    rpm_limit: int | None = None

    tracing_enabled: bool = False
    tracing_tags: list[str] = field(default_factory=list)
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    langfuse_mask_content: bool = True

    chat_stream_include_usage: bool = True
    chat_max_output_tokens: int = 1200
    web_timeout_seconds: float = 8.0
    tavily_api_key: str | None = None

    def __post_init__(self) -> None:
        if not self.routes:
            raise ConfigurationError("routes are required in AiConfig.")
        for name, route in self.routes.items():
            if not route.primary.model or not route.primary.api_key:
                raise ConfigurationError(
                    f"{name} primary model and api key are required."
                )
            for idx, fb in enumerate(route.fallbacks, start=1):
                if not fb.model or not fb.api_key:
                    raise ConfigurationError(
                        f"{name} fallback #{idx} model and api key are required."
                    )

    @property
    def has_chat(self) -> bool:
        return "chat" in self.routes

    @property
    def has_plan(self) -> bool:
        return "plan" in self.routes

    @property
    def has_embed(self) -> bool:
        return "embed" in self.routes

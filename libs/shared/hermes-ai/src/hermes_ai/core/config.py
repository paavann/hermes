from dataclasses import dataclass, field


@dataclass(frozen=True)
class AiConfig:
    primary_model: str
    primary_api_key: str
    fallback_model: str | None = None
    fallback_api_key: str | None = None
    embed_model: str | None = None
    embed_api_key: str | None = None
    num_retries: int = 2
    cooldown_time: int = 180
    retry_after: bool = True
    rpm_limit: int | None = None
    embed_rpm_limit: int | None = None
    tracing_enabled: bool = False
    tracing_tags: list[str] = field(default_factory=list)
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None

    @property
    def has_fallback(self) -> bool:
        return self.fallback_model is not None

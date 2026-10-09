"""Configuration models for Hermes AI services."""

from dataclasses import dataclass


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

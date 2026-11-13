import os
from pathlib import Path
from functools import lru_cache
from typing import Literal, Self
from pydantic import AliasChoices, Field, SecretStr, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


# anchor paths relative to this file rather than the current working directory.
# adjust `.parents[2]` depending on how deep this file sits inside your repo.
SERVICE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_DIR.parents[1]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True,
    )

    # worker metadata.
    APP: str = "hermes-worker"
    ENV: Literal["development", "staging", "production"] = "development"
    VERSION: str = "1.0.0"

    # db credentials.
    DB_HOST: str = "localhost"
    DB_PORT: int = Field(default=5432, gt=0, le=65535)
    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr
    DB_NAME: str = "hermes"
    DB_SSL_MODE: Literal["disable", "allow", "prefer", "require"] | None = None

    # primary and fallback llm credentials.
    LLM_API: SecretStr = SecretStr("")
    LLM_API_1: SecretStr | None = None
    LLM_MODEL: str = ""
    LLM_MODEL_1: str | None = None

    # primary and fallback embedding credentials.
    EMBED_API: SecretStr = SecretStr("")
    EMBED_API_1: SecretStr | None = None
    EMBED_MODEL: str = ""
    EMBED_MODEL_1: str | None = None

    # rate limits.
    RPM_LIMIT: int = Field(default=26, gt=0)
    EMBED_RPM_LIMIT: int = Field(default=90, gt=0)

    # nominatim geocoding user agent.
    NOMINATIM_USER_AGENT: str = (
        "HermesGeospatialNews/1.0 (https://github.com/paavann/hermes)"
    )

    # langfuse tracing.
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: SecretStr = SecretStr("")
    LANGFUSE_HOST: HttpUrl = Field(
        default=HttpUrl("https://cloud.langfuse.com"),
        validation_alias=AliasChoices("LANGFUSE_HOST", "LANGFUSE_BASE_URL"),
    )

    # sync configuration.
    RSS_FETCH_INTERVAL_MIN: int = Field(default=15, gt=0)
    SYNC_INTERVAL_MIN: int = Field(default=360, gt=0)
    EVENT_STALE_HOURS: int = Field(default=24, gt=0)
    EVENT_ARCHIVE_HOURS: int = Field(default=48, gt=0)

    @model_validator(mode="after")
    def validate_semantics(self) -> Self:
        if self.EVENT_ARCHIVE_HOURS <= self.EVENT_STALE_HOURS:
            raise ValueError(
                "EVENT_ARCHIVE_HOURS must be greater than EVENT_STALE_HOURS"
            )
        if self.ENV == "production":
            missing = [
                name
                for name, val in (
                    ("LLM_API", self.LLM_API.get_secret_value()),
                    ("LLM_MODEL", self.LLM_MODEL),
                    ("EMBED_API", self.EMBED_API.get_secret_value()),
                    ("EMBED_MODEL", self.EMBED_MODEL),
                )
                if not val
            ]
            if missing:
                raise ValueError(
                    f"Missing required production settings: {', '.join(missing)}"
                )
        return self

    @property
    def db_url(self) -> URL:
        query: dict[str, str] = {}
        if self.DB_SSL_MODE is not None:
            query["ssl"] = self.DB_SSL_MODE
        elif self.ENV != "development":
            query["ssl"] = "require"
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD.get_secret_value(),
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query=query,
        )


def _resolve_env_files(env: str) -> tuple[Path, ...]:
    return (
        REPO_ROOT / ".env",
        REPO_ROOT / f".env.{env}",
        REPO_ROOT / ".env.local",
        REPO_ROOT / f".env.{env}.local",
        SERVICE_DIR / ".env",
        SERVICE_DIR / f".env.{env}",
        SERVICE_DIR / ".env.local",
        SERVICE_DIR / f".env.{env}.local",
    )

@lru_cache
def get_settings() -> Settings:
    # bootstrap ENV strictly from the process environment so it stays consistent
    # with the .env.<env> files being loaded.
    raw_env = os.getenv("ENV", "development").strip().lower()
    env_files = _resolve_env_files(raw_env)

    # ensure ENV inside Settings matches the process environment rather than
    # being silently overridden by a base .env file.
    return Settings(ENV=raw_env, _env_file=env_files) # type: ignore[arg-type]


def __getattr__(name: str) -> Settings:
    if name == "settings":
        return get_settings()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

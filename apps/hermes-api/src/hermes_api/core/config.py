from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    APP: str = "hermes"
    ENV: str = "dev"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "hermes"

    # Primary LLM (Index 0)
    LLM_API: str = ""
    LLM_MODEL: str = "mistral/ministral-8b-latest"

    # Secondary / Fallback LLM (Index 1)
    LLM_API_1: Optional[str] = None
    LLM_MODEL_1: Optional[str] = "nvidia_nim/mistralai/mistral-nemotron"

    # Primary Embeddings (Index 0)
    EMBED_API: str = ""
    EMBED_MODEL: str = "nvidia_nim/nvidia/nemotron-3-embed-1b"

    # Secondary / Fallback Embeddings (Index 1, optional)
    EMBED_API_1: Optional[str] = None
    EMBED_MODEL_1: Optional[str] = None

    # Backward compatibility aliases
    LLM_API_KEY: Optional[str] = None
    LLM_API_KEY_1: Optional[str] = None
    LLM_MODEL_2: Optional[str] = None
    LLM_API_KEY_2: Optional[str] = None
    EMBED_API_KEY: Optional[str] = None

    @property
    def primary_llm_model(self) -> str:
        return self.LLM_MODEL

    @property
    def primary_llm_api(self) -> str:
        return self.LLM_API or self.LLM_API_KEY or self.LLM_API_KEY_1 or ""

    @property
    def fallback_llm_model(self) -> str:
        return self.LLM_MODEL_1 or self.LLM_MODEL_2 or "nvidia_nim/mistralai/mistral-nemotron"

    @property
    def fallback_llm_api(self) -> str:
        return self.LLM_API_1 or self.LLM_API_KEY_2 or self.primary_embed_api

    @property
    def primary_embed_api(self) -> str:
        return self.EMBED_API or self.EMBED_API_KEY or ""

    @property
    def normalized_embed_model(self) -> str:
        if self.EMBED_MODEL.startswith("nvidia/") and not self.EMBED_MODEL.startswith("nvidia_nim/"):
            return f"nvidia_nim/{self.EMBED_MODEL}"
        return self.EMBED_MODEL

    NOMINATIM_USER_AGENT: str = "HermesGeospatialNews/1.0 (https://github.com/paavann/hermes)"

    RSS_FETCH_INTERVAL_MIN: int = 15
    INGESTION_HEARTBEAT_MIN: int = 360

    RPM_LIMIT: int = 26
    EMBED_RPM_LIMIT: int = 90

    EVENT_STALE_HOURS: int = 24
    EVENT_ARCHIVE_HOURS: int = 48

    @property
    def db_url(self) -> URL:
        query = {}
        if self.DB_HOST not in ("localhost", "hermes-db", "127.0.0.1"):
            query["ssl"] = "require"

        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query=query,
        )

    @property
    def direct_db_url(self) -> URL:
        """Direct (unpooled) PostgreSQL URL for schema migrations and administrative DDL.
        Neon and PgBouncer pooled hosts contain '-pooler' in the hostname.
        Alembic migrations require direct session connections for PostgreSQL advisory locks and DDL.
        """
        query = {}
        if self.DB_HOST not in ("localhost", "hermes-db", "127.0.0.1"):
            query["ssl"] = "require"

        direct_host = self.DB_HOST.replace("-pooler", "")
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=direct_host,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query=query,
        )

    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

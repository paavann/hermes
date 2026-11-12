import os
from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # server metadata.
    APP: str = "hermes"
    ENV: str = "development"
    API_PORT: int
    VERSION: str = "1.0.0"
    API_BASE_PATH: str = "/api/v1"

    # db credentials.
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # primary and fallback llm (secondary) credentials.
    LLM_API: str = ""
    LLM_MODEL: str = ""
    LLM_API_1: str | None = None
    LLM_MODEL_1: str | None = None

    # primary and fallback embed model (secondary) credentials.
    EMBED_API: str = ""
    EMBED_MODEL: str = ""
    EMBED_API_1: str | None = None
    EMBED_MODEL_1: str | None = None

    # rate limit configuration.
    RPM_LIMIT: int = 26
    EMBED_RPM_LIMIT: int = 90

    # nominatim geocoding service.
    NOMINATIM_USER_AGENT: str = (
        "HermesGeospatialNews/1.0 (https://github.com/paavann/hermes)"
    )

    # chat configuration.
    CHAT_ENABLED: bool = True
    CHAT_MODEL: str = ""
    CHAT_API: str = ""
    CHAT_MODEL_1: str | None = None
    CHAT_API_1: str | None = None
    PLAN_MODEL: str = ""
    PLAN_API: str = ""
    PLAN_MODEL_1: str | None = None
    PLAN_API_1: str | None = None
    TAVILY_API_KEY: str = ""

    # chat router and request guards.
    CHAT_RPM_LIMIT: int = 60
    CHAT_RATE_LIMIT_REQUESTS: int = 10
    CHAT_RATE_LIMIT_WINDOW_SECONDS: int = 60
    CHAT_DAILY_TOKEN_BUDGET: int = 500_000
    CHAT_MAX_CONCURRENT: int = 4
    CHAT_QUEUE_TIMEOUT_SECONDS: float = 5.0
    TRUST_PROXY_HEADERS: bool = False

    # chat retrieval and answer limits.
    CHAT_RETRIEVAL_TOP_K: int = 8
    CHAT_MIN_LOCAL_RESULTS: int = 2
    CHAT_MIN_SEMANTIC_SIMILARITY: float = 0.20
    CHAT_FRESHNESS_HOURS: int = 24
    CHAT_MAX_MESSAGE_CHARS: int = 4000
    CHAT_MAX_HISTORY_TURNS: int = 8
    CHAT_MAX_OUTPUT_TOKENS: int = 1200
    CHAT_WEB_TIMEOUT_SECONDS: float = 8.0
    CHAT_STREAM_INCLUDE_USAGE: bool = True

    # cors configuration.
    CORS_ORIGINS: list[str] = ["*"]

    # langfuse tracing.
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = Field(
        default="https://cloud.langfuse.com",
        validation_alias=AliasChoices("LANGFUSE_HOST", "LANGFUSE_BASE_URL"),
    )
    LANGFUSE_BASE_URL: str | None = None
    LANGFUSE_MASK_CONTENT: bool = True

    # database connection url.
    @property
    def db_url(self) -> URL:
        query = {}
        host = self.DB_HOST
        if host not in ("localhost", "127.0.0.1", "hermes-db"):
            query["ssl"] = "require"
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=host,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query=query,
        )


@lru_cache
def get_settings() -> Settings:
    env = os.getenv("ENV", "development").lower()
    env_files = (
        "../../.env",
        f"../../.env.{env}",
        "../../.env.local",
        f"../../.env.{env}.local",
        ".env",
        f".env.{env}",
        ".env.local",
        f".env.{env}.local",
    )
    return Settings(_env_file=env_files)  # pyright: ignore[reportCallIssue]


settings = get_settings()

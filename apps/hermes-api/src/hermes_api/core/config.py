from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    APP: str = "hermes"
    ENV: str = "dev"
    FRONTEND_URL: str = "http://localhost:4200"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "hermes"

    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini/gemini-3.6-flash"
    EMBED_API_KEY: str = ""
    EMBED_MODEL: str = "gemini/embedding-001"

    NOMINATIM_USER_AGENT: str = "hermes-api"

    RSS_FETCH_INTERVAL_MINUTES: int = 15

    INGESTION_HEARTBEAT_MINUTES: int = 5
    GEMINI_RPM_LIMIT: int = 5
    GEMINI_EMBED_RPM_LIMIT: int = 100

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

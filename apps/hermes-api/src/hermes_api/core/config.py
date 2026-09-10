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

    GEMINI_API_KEY: str = ""

    NOMINATIM_USER_AGENT: str = "hermes-api"

    RSS_FETCH_INTERVAL_MINUTES: int = 15

    INGESTION_CRON_HOURS: str = "6,14,22"
    GEMINI_RPM_LIMIT: int = 15

    EVENT_STALE_HOURS: int = 24
    EVENT_ARCHIVE_HOURS: int = 48

    @property
    def db_url(self) -> URL:
        query = {}
        if self.DB_HOST != "localhost":
            query["ssl"] = "require"

        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query=query
        )

    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )



@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
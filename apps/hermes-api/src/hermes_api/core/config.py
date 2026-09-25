from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL







class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )



    # server metadata.
    APP: str = "hermes"
    ENV: str = "dev"



    # db credentials.
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "hermes"



    # primary llm credentials.
    LLM_API: str = ""
    LLM_MODEL: str = ""

    # fallback llm credentials (secondary).
    LLM_API_1: Optional[str] = None
    LLM_MODEL_1: Optional[str] = None

    # primary embedding llm credentials.
    EMBED_API: str = ""
    EMBED_MODEL: str = ""

    # fallback embeddings llm credentials (secondary).
    EMBED_API_1: Optional[str] = None
    EMBED_MODEL_1: Optional[str] = None

    # rate limit configuration.
    RPM_LIMIT: int = 26
    EMBED_RPM_LIMIT: int = 90



    # nominatim geocoding service.
    NOMINATIM_USER_AGENT: str = "HermesGeospatialNews/1.0 (https://github.com/paavann/hermes)"



    # ingestion configuration.
    RSS_FETCH_INTERVAL_MIN: int = 15
    INGESTION_HEARTBEAT_MIN: int = 360
    EVENT_STALE_HOURS: int = 24
    EVENT_ARCHIVE_HOURS: int = 48



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
    return Settings()

settings = get_settings()

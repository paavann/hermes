import os
from pydantic_settings import SettingsConfigDict
from functools import lru_cache
from pydantic_settings import BaseSettings
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "development"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "hermes"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""

    @property
    def db_url(self) -> URL:
        query = {}
        if self.DB_HOST not in ("localhost", "127.0.0.1", "hermes-db"):
            query["sssl"] = "require"
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query=query,
        )


@lru_cache
def get_settings() -> Settings:
    env = os.getenv("ENV", "development")
    return Settings(
        _env_file=(
            f".env.{env}",
            ".env",
            f"../../../.env.{env}",
            "../../../.env",
        )
    )


settings = get_settings()
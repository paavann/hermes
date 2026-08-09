from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from sqlalchemy import URL




class Settings(BaseSettings):
    APP: str = "hermes"
    ENV: str = "dev"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "hermes"

    @property
    def db_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )



@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
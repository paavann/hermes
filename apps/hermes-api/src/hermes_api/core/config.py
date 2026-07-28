from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache




class Settings(BaseSettings):
    APP: str = "hermes"
    ENV: str = "dev"

    DB_URL: str

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
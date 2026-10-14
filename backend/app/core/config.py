from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Software Engineering Agent Platform"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    database_url: str = ""
    postgres_password: str = ""

    jwt_secret_key: str = ""

    gemini_api_key: str = ""

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_database: int = 0
    redis_password: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
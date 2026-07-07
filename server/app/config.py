import logging
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"

    langsmith_tracing: bool = True
    langsmith_api_key: str = ""
    langsmith_project: str = "signals-langraph-agent"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    log_level: str = "INFO"

    signals_default_user_name: str | None = None

    database_url: str = "postgresql+psycopg://signals:signals@localhost:5432/signals"
    jwt_secret: str = "change-me-in-production"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7
    cors_origins: list[str] = ["http://localhost:3000"]
    api_base_url: str = "http://localhost:8000"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def configure_langsmith() -> None:
    """Apply LangSmith env vars so tracing works for CLI and Studio."""
    if settings.langsmith_tracing:
        os.environ["LANGSMITH_TRACING"] = "true"
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_project:
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint

"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings with validation from env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    github_token: str
    anthropic_api_key: str
    webhook_secret: str
    skip_draft_prs: bool = True
    log_level: str = "INFO"


def get_settings() -> Settings:
    """Return validated settings instance."""
    return Settings()

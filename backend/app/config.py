from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration is sourced from environment variables (or a local .env
    file during development). Nothing sensitive ever has a default value or
    lives in source control - see .env.example for the full list of keys.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LinkedIn session (see README "Authentication" section for how to obtain these).
    linkedin_li_at: str | None = None
    linkedin_jsessionid: str | None = None
    linkedin_extra_cookies: str | None = None
    linkedin_user_agent: str | None = None

    # HTTP behaviour against LinkedIn.
    request_timeout_seconds: float = 15.0
    max_retries: int = 3
    retry_backoff_seconds: float = 1.5

    # Service.
    log_level: str = "INFO"
    cors_origins: str = "*"
    environment: str = "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def has_linkedin_session(self) -> bool:
        return bool(self.linkedin_li_at)


@lru_cache
def get_settings() -> Settings:
    return Settings()

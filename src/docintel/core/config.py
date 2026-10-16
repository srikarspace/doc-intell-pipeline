"""Settings from env vars and `.env`. One place for keys, URLs and defaults."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: SecretStr
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    docintel_model: str = "qwen/qwen3-235b-a22b-2507"
    llm_timeout_s: float = 120.0
    llm_max_attempts: int = 4  # 1 try + 3 retries, only for network errors and 429


@lru_cache
def get_settings() -> Settings:
    """Read the settings once, then reuse them."""
    return Settings()

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GUARDIAN_", env_file=".env")

    database_url: str = "postgresql+asyncpg://guardian:guardian@localhost:5432/guardian"
    jwt_secret: str = Field(min_length=32)
    access_minutes: int = 15
    refresh_days: int = 30
    policy_key_id: str = "guardian-dev"
    policy_private_key: str | None = None
    health_stale_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings(jwt_secret="development-only-change-me-please-32")

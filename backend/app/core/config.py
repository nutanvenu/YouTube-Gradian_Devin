import base64
import json
import os
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GUARDIAN_", env_file=".env")

    database_url: str = "postgresql+asyncpg://guardian:guardian@localhost:5432/guardian"
    environment: Literal["development", "test", "production"] = "development"
    jwt_secret: str = Field(min_length=32)
    access_minutes: int = 15
    refresh_days: int = 30
    policy_key_id: str = "guardian-dev"
    policy_private_key: str | None = None
    policy_trusted_public_keys: str | None = None
    health_stale_minutes: int = 15

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment != "production":
            return self

        weak_markers = ("change-me", "replace", "placeholder", "development", "example", "fixture")
        if len(self.jwt_secret) < 32 or any(
            marker in self.jwt_secret.lower() for marker in weak_markers
        ):
            raise ValueError(
                "production JWT secret must be a non-placeholder value of at least 32 characters"
            )
        if not self.policy_private_key:
            raise ValueError("production policy private key must be configured")
        try:
            if len(base64.b64decode(self.policy_private_key, validate=True)) != 32:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError(
                "production policy private key must be a base64-encoded 32-byte Ed25519 key"
            ) from None
        try:
            trusted_keys = json.loads(self.policy_trusted_public_keys or "")
            if not isinstance(trusted_keys, dict) or not trusted_keys:
                raise ValueError
            if self.policy_key_id not in trusted_keys:
                raise ValueError
            if any(
                not isinstance(key_id, str)
                or not isinstance(encoded_key, str)
                or len(base64.b64decode(encoded_key, validate=True)) != 32
                for key_id, encoded_key in trusted_keys.items()
            ):
                raise ValueError
        except (ValueError, TypeError, json.JSONDecodeError):
            raise ValueError(
                "production trusted policy public keys must be a non-empty Ed25519 JSON object "
                "containing the active key"
            ) from None
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings(
        jwt_secret=os.environ.get(
            "GUARDIAN_JWT_SECRET", "development-only-change-me-please-32"
        )
    )

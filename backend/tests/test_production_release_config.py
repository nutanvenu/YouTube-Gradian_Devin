import base64

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides: object) -> Settings:
    private_key = base64.b64encode(bytes(range(32))).decode("ascii")
    public_key = base64.b64encode(bytes(range(32, 64))).decode("ascii")
    values: dict[str, object] = {
        "environment": "production",
        "jwt_secret": "production-secret-that-is-not-a-placeholder-12345",
        "policy_key_id": "guardian-prod-2026-01",
        "policy_private_key": private_key,
        "policy_trusted_public_keys": '{"guardian-prod-2026-01":"' + public_key + '"}',
    }
    values.update(overrides)
    return Settings(**values)


def test_production_settings_reject_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT secret"):
        production_settings(jwt_secret="development-only-change-me-please-32")


def test_production_settings_reject_missing_or_invalid_policy_secrets() -> None:
    with pytest.raises(ValidationError, match="policy private key"):
        production_settings(policy_private_key=None)
    with pytest.raises(ValidationError, match="trusted policy public key"):
        production_settings(policy_trusted_public_keys="{}")


def test_production_settings_accepts_non_placeholder_signing_configuration() -> None:
    settings = production_settings()
    assert settings.environment == "production"

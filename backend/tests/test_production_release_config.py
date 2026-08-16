import base64

import pytest
from pydantic import ValidationError

from app.core.config import get_settings


def test_get_settings_uses_valid_production_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    public_key = base64.b64encode(bytes(range(32))).decode("ascii")
    monkeypatch.setenv("GUARDIAN_ENVIRONMENT", "production")
    monkeypatch.setenv("GUARDIAN_JWT_SECRET", "production-secret-with-sufficient-entropy-12345")
    monkeypatch.setenv("GUARDIAN_POLICY_KEY_ID", "guardian-prod-2026-01")
    monkeypatch.setenv("GUARDIAN_POLICY_PRIVATE_KEY", public_key)
    monkeypatch.setenv(
        "GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS",
        '{"guardian-prod-2026-01":"' + public_key + '"}',
    )
    get_settings.cache_clear()
    try:
        assert get_settings().environment == "production"
    finally:
        get_settings.cache_clear()


def test_get_settings_rejects_production_when_default_jwt_would_be_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_ENVIRONMENT", "production")
    monkeypatch.delenv("GUARDIAN_JWT_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(ValidationError, match="JWT secret"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_get_settings_honors_dotenv_jwt_secret_without_an_environment_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    dotenv_secret = "dotenv-production-secret-with-sufficient-entropy-12345"
    (tmp_path / ".env").write_text(f"GUARDIAN_JWT_SECRET={dotenv_secret}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GUARDIAN_JWT_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        assert get_settings().jwt_secret == dotenv_secret
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    ("key_id", "public_key"),
    [
        ("guardian-example", base64.b64encode(bytes(range(32))).decode("ascii")),
        ("guardian-prod-2026-01", base64.b64encode(bytes(range(32))).decode("ascii") + "\n"),
    ],
)
def test_get_settings_rejects_placeholder_key_ids_and_noncanonical_public_keys(
    monkeypatch: pytest.MonkeyPatch, key_id: str, public_key: str
) -> None:
    private_key = base64.b64encode(bytes(range(32))).decode("ascii")
    monkeypatch.setenv("GUARDIAN_ENVIRONMENT", "production")
    monkeypatch.setenv("GUARDIAN_JWT_SECRET", "production-secret-with-sufficient-entropy-12345")
    monkeypatch.setenv("GUARDIAN_POLICY_KEY_ID", key_id)
    monkeypatch.setenv("GUARDIAN_POLICY_PRIVATE_KEY", private_key)
    monkeypatch.setenv(
        "GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS", f'{{"{key_id}":"{public_key}"}}'
    )
    get_settings.cache_clear()
    try:
        with pytest.raises(ValidationError, match="trusted policy public keys"):
            get_settings()
    finally:
        get_settings.cache_clear()

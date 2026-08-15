import base64
import json
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.config import get_settings
from app.policies.service import default_policy
from app.policies.signing import (
    canonical_bytes,
    signer,
    validate_policy_bundle,
    verify_signed_bundle,
)


@pytest.fixture
def signing_key() -> str:
    raw = bytes(range(32))
    settings = get_settings()
    previous = settings.policy_private_key
    settings.policy_private_key = base64.b64encode(raw).decode("ascii")
    settings.policy_key_id = "test-key"
    signer._private_key = None
    try:
        yield settings.policy_private_key
    finally:
        settings.policy_private_key = previous
        signer._private_key = None


def test_python_canonical_bytes_are_stable_for_nested_unicode_values() -> None:
    fixture = json.loads(
        (
            Path(__file__).parents[2]
            / "packages"
            / "policy-schema"
            / "test-fixtures"
            / "canonical-cross-language.json"
        ).read_text()
    )
    assert base64.b64encode(canonical_bytes(fixture["value"])).decode("ascii") == fixture[
        "canonical_utf8_base64"
    ]


def test_signer_validates_and_signs_a_policy_bundle(signing_key: str) -> None:
    bundle = default_policy(uuid4(), uuid4(), "TEEN", "UTC")
    signed = signer.sign(bundle)
    assert signed["key_id"] == "test-key"
    assert isinstance(signed["signature"], str)
    assert signed["signature"]
    validate_policy_bundle(signed)
    public_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32))).public_key()
    signature = base64.b64decode(str(signed["signature"]))
    public_key.verify(signature, canonical_bytes(signed))


def test_python_verifies_the_typescript_signature_fixture() -> None:
    fixture = json.loads(
        (
            Path(__file__).parents[2]
            / "packages"
            / "policy-schema"
            / "test-fixtures"
            / "signature-cross-language.json"
        ).read_text()
    )
    public_key = Ed25519PrivateKey.from_private_bytes(
        bytes.fromhex(fixture["private_key_seed"])
    ).public_key()
    public_key.verify(
        base64.b64decode(fixture["signature"]),
        canonical_bytes(fixture["bundle"]),
    )


def test_trusted_key_set_rejects_unknown_rotated_out_and_tampered_bundles() -> None:
    fixture = json.loads(
        (
            Path(__file__).parents[2]
            / "packages"
            / "policy-schema"
            / "test-fixtures"
            / "signature-cross-language.json"
        ).read_text()
    )
    bundle = {**fixture["bundle"], "signature": fixture["signature"]}
    trusted = {"fixture-key": fixture["public_key"]}
    assert verify_signed_bundle(bundle, trusted)
    assert not verify_signed_bundle(bundle, {})
    assert not verify_signed_bundle(bundle, {"old-key": fixture["public_key"]})
    tampered = {**bundle, "family_id": "tampered"}
    assert not verify_signed_bundle(tampered, trusted)

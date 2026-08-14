import base64
import json
from collections.abc import Mapping
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from jsonschema import Draft202012Validator, FormatChecker

from ..core.config import get_settings

SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "policy-schema"
    / "schema"
    / "policy-bundle.schema.json"
)


def _reject_surrogates(value: object) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ValueError("Canonical JSON does not permit lone surrogates")
    elif isinstance(value, Mapping):
        for key, child in value.items():
            _reject_surrogates(key)
            _reject_surrogates(child)
    elif isinstance(value, list):
        for child in value:
            _reject_surrogates(child)


def _canonical(value: object) -> str:
    _reject_surrogates(value)
    if value is None or isinstance(value, bool):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    if isinstance(value, int):
        if not -(2**53 - 1) <= value <= 2**53 - 1:
            raise ValueError("Canonical JSON permits only safe integers")
        return str(value)
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("Canonical JSON permits only integers")
        return str(int(value))
    if isinstance(value, str):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(_canonical(child) for child in value) + "]"
    if isinstance(value, Mapping):
        keys = sorted(value, key=lambda key: str(key).encode("utf-16-be", "surrogatepass"))
        return "{" + ",".join(
            _canonical(str(key)) + ":" + _canonical(value[key]) for key in keys
        ) + "}"
    raise TypeError(f"Unsupported canonical JSON value: {type(value).__name__}")


def canonical_bytes(bundle: Mapping[str, object]) -> bytes:
    unsigned = {key: value for key, value in bundle.items() if key != "signature"}
    return _canonical(unsigned).encode("utf-8")


def validate_policy_bundle(bundle: dict[str, object]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(bundle)
    )
    if errors:
        raise ValueError(
            "Policy bundle validation failed: " + "; ".join(error.message for error in errors)
        )


class PolicySigner:
    def __init__(self) -> None:
        self._private_key: Ed25519PrivateKey | None = None

    def _key(self) -> Ed25519PrivateKey:
        settings = get_settings()
        if not settings.policy_private_key:
            raise RuntimeError("GUARDIAN_POLICY_PRIVATE_KEY is not configured")
        if self._private_key is None:
            raw = base64.b64decode(settings.policy_private_key, validate=True)
            if len(raw) != 32:
                raise RuntimeError("GUARDIAN_POLICY_PRIVATE_KEY must decode to 32 bytes")
            self._private_key = Ed25519PrivateKey.from_private_bytes(raw)
        return self._private_key

    def sign(self, bundle: dict[str, object]) -> dict[str, object]:
        settings = get_settings()
        bundle["key_id"] = settings.policy_key_id
        bundle["signature"] = ""
        validate_policy_bundle(bundle)
        signature = self._key().sign(canonical_bytes(bundle))
        bundle["signature"] = base64.b64encode(signature).decode("ascii")
        return bundle

    def public_key(self) -> str:
        raw = self._key().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return base64.b64encode(raw).decode("ascii")


signer = PolicySigner()

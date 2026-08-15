import base64
from collections.abc import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ..policies.signing import canonical_bytes, configured_trusted_public_keys, signer


def sign_reputation(document: dict[str, object]) -> dict[str, object]:
    return signer.sign_document(document)


def verify_signed_reputation(
    document: Mapping[str, object], trusted_public_keys: Mapping[str, str]
) -> bool:
    key_id = document.get("key_id")
    signature = document.get("signature")
    if not isinstance(key_id, str) or not isinstance(signature, str):
        return False
    encoded_key = trusted_public_keys.get(key_id)
    if encoded_key is None:
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(encoded_key, validate=True)
        )
        public_key.verify(
            base64.b64decode(signature, validate=True),
            canonical_bytes(document),
        )
    except (InvalidSignature, ValueError, TypeError):
        return False
    return True


def configured_reputation_keys() -> dict[str, str]:
    return configured_trusted_public_keys()

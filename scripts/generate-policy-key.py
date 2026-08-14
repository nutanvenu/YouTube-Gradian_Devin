#!/usr/bin/env python3
"""Generate an Ed25519 policy signing key for local secret storage."""

import base64
import secrets


def main() -> None:
    print(base64.b64encode(secrets.token_bytes(32)).decode("ascii"))


if __name__ == "__main__":
    main()

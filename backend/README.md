# Guardian backend

The backend is a FastAPI modular monolith using SQLAlchemy 2 async sessions,
Alembic migrations, and PostgreSQL 16. Application code never calls
`metadata.create_all`; schema changes are applied with:

```bash
docker compose up -d postgres
uv sync --locked --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Python dependencies are managed exclusively with `uv`. The repository pins
the tool version in `.uv-version`, pins application and development
dependencies in `pyproject.toml`, and records the resolved artifacts in
`uv.lock`. Use `uv sync --locked` locally and in CI; do not maintain a
parallel `requirements.txt` file.

Authentication uses Argon2id password hashes, short-lived access JWTs, and
hashed rotating refresh tokens. Configure secrets through environment
variables; never commit `.env`.

## Local policy signing key

The backend refuses to start when `GUARDIAN_POLICY_PRIVATE_KEY` is absent,
not base64, or does not decode to exactly 32 bytes. Generate a local Ed25519
key and place it in the ignored `backend/.env` file:

```bash
python -c 'import base64; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat; key=Ed25519PrivateKey.generate(); print(base64.b64encode(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).decode())'
```

Set the generated value as `GUARDIAN_POLICY_PRIVATE_KEY`. The matching public
key is exposed by `GET /v1/policy/public-key`; do not commit the private key.

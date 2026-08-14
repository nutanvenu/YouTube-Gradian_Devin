# Guardian backend

The backend is a FastAPI modular monolith using SQLAlchemy 2 async sessions,
Alembic migrations, and PostgreSQL 16. Application code never calls
`metadata.create_all`; schema changes are applied with:

```bash
docker compose up -d postgres
source "$HOME/.pyenv/bin/pyenv" 2>/dev/null || true
alembic upgrade head
uvicorn app.main:app --reload
```

Authentication uses Argon2id password hashes, short-lived access JWTs, and
hashed rotating refresh tokens. Configure secrets through environment
variables; never commit `.env`.

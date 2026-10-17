# Deploy on Vercel serverless + Neon Postgres, not Fly.io

We run the bot as Telegram **webhooks** on a Vercel Python function (Hobby, non-commercial, $0) with **Neon Postgres** (`asyncpg`) in prod and SQLite (`aiosqlite`) locally, instead of an always-on Fly.io machine with long polling. Fly.io was rejected: new orgs have no free tier, a ~$3.9/mo always-on 256 MB machine OOMs (importing aiogram+pydantic+sqlalchemy ≈ 196 MB), and only long polling was available there. Webhooks also remove the need for offline status updates: Telegram retries undelivered updates with backoff and the function wakes on each request.

## Considered Options

- **Fly.io + long polling** — rejected on cost and memory (above). `Dockerfile`/`fly.toml` are kept only as an optional, non-prod deploy path.
- **Turso (libSQL)** — rejected: `sqlalchemy-libsql` has no async engine; would mean rewriting the repository layer.
- **Oracle/GCP/AWS** — rejected on card/geo constraints (Belarus).

## Consequences

- Prod and local use different dialects; migrations must stay dialect-agnostic and an integration test guards SQLite↔Postgres drift (`tests/integration/test_postgres_repo.py`, opt-in via `TEST_DATABASE_URL`).
- `data/` volume deploy is not the production path.

## Implementation (P6 / SPEC-006)

- Webhook ASGI app: `src/adapters/webhook/app.py` (`create_app`, `POST /webhook`, `GET /` health), exposed to Vercel via `asgi.py` + `[tool.vercel] entrypoint`.
- Shared wiring for polling and webhook: `src/infrastructure/bootstrap.py`.
- Register/unregister: `python -m src.adapters.webhook.manage set|delete|info` (`make webhook-*`); `WEBHOOK_SECRET` verified against the `X-Telegram-Bot-Api-Secret-Token` header.
- Postgres URL params (`sslmode`/`channel_binding`) are normalized to asyncpg's `ssl`, and a bare `postgresql://` URL is upgraded to the `asyncpg` driver, in `src/infrastructure/db.py`; `alembic/env.py` loads `.env` so `make migrate` targets the same database as the app. the schema is Alembic-owned on both dialects (`init_db` only enables SQLite WAL and fails fast when migrations are missing).

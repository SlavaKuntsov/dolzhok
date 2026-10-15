# SPEC-004 — deploy 24/7 on Fly.io (P4)

## Goal
Run the bot unattended on Fly.io free tier: one always-on worker machine, a
1 GB volume mounted at `/data` so the SQLite file survives restarts/redeploys,
secrets injected as Fly secrets, and the schema applied from Alembic migrations
before the bot starts. Document the operational runbook (logs, catch-up after a
restart, backup/restore) so either party can operate it without guesswork.

## Design
- **No HTTP.** The bot is a pure long-polling worker; `fly.toml` has no
  `http_service`/`services`, so Fly keeps the machine running without health
  checks or a public port.
- **Volume.** `fly volumes create data --size 1 --region ams` mounted at `/data`;
  `DATABASE_URL=sqlite+aiosqlite:////data/bot.db` (WAL enabled at startup).
- **Secrets.** `BOT_TOKEN`, `DAD_ID`, `SON_ID` come from `fly secrets set` (env),
  never from the image. `.env` is not shipped (see `.dockerignore`).
- **Migrations on boot.** `docker-entrypoint.sh` runs `.venv/bin/alembic upgrade head`
  against `DATABASE_URL`, then `exec`s the bot from the venv (Python is PID 1, so
  Fly's stop signal is handled directly). `alembic/env.py` prefers the
  `DATABASE_URL` env var over the `alembic.ini` default, so the container migrates
  the volume DB, not a local path. `init_db`'s `create_all` remains as an
  idempotent safety net for a fresh file.
- **Catch-up.** `long polling` + `delete_webhook(drop_pending_updates=False)`:
  Telegram keeps unconfirmed updates < 24h, so a restart resumes and drains the
  queue. Nothing is stored on the client.

## Flows
1. First deploy: `fly launch --no-deploy` (uses `Dockerfile`, app `tg-bot-dad-ozon`,
   region `ams`) → `fly volumes create data --size 1 --region ams` →
   `fly secrets set BOT_TOKEN=... DAD_ID=... SON_ID=...` → `fly deploy`.
2. Each boot: entrypoint migrates `/data/bot.db` to head, then starts polling.
3. Restart/redeploy: same machine, same volume → DB intact, queued updates drained.
4. Operate: `make logs` (tail), `make backup` (dump to dated `.sql`), `make restore`
   (drop the volume DB, load the dump into an empty file, restart the machine).

## Acceptance criteria
- Given `docker-entrypoint.sh` and `DATABASE_URL` set When the container starts
  Then `alembic upgrade head` runs against that URL before the bot process.
- Given `DATABASE_URL` unset When Alembic runs Then it falls back to the
  `alembic.ini` `sqlalchemy.url` (local quickstart unchanged).
- Given a fresh `/data` volume When the app boots Then the DB file is created with
  all migrations applied and WAL enabled.
- Given a restart with updates queued When the bot resumes Then it processes them
  (`drop_pending_updates=False`), no data loss for gaps < 24h.
- Given `.dockerignore` When the image is built Then no `.env`, `data/`, `*.db`,
  `.venv/`, or `.git/` is copied in.
- Given README `Deploy` section When followed top-to-bottom Then the runbook covers
  deploy, logs, catch-up, backup and restore.
- Given a `make backup` dump When `make restore FILE=...` runs Then the volume DB is
  rebuilt from an empty file (no `table already exists`) and the machine restarts.
- Given `make restore` without `FILE=` When it runs Then it exits with a usage
  message instead of blocking on stdin.

## Out of scope
- Turso/libsql migration (separate `IItemRepository` implementation).
- CI/CD automation, alerting, metrics, horizontal scaling (`min_machines_running`
  stays 1 — SQLite is single-writer).
- Postgres and multi-family support.

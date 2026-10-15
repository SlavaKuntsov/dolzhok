#!/bin/sh
# Container entrypoint: bring the volume DB to head, then start the bot.
#
# DATABASE_URL comes from Fly secrets; alembic/env.py prefers it over alembic.ini
# so migrations always target the mounted volume. The venv binaries are invoked
# directly so Python (not `uv`) is PID 1 and receives Fly's stop signal.
set -eu

echo "[entrypoint] applying migrations (alembic upgrade head)..."
/app/.venv/bin/alembic upgrade head

echo "[entrypoint] starting bot (long polling)..."
exec /app/.venv/bin/python -m src.main
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .python-version ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/ 2>/dev/null || true

RUN mkdir -p /data

CMD ["uv", "run", "python", "-m", "src.main"]

"""Vercel ASGI entrypoint (see `[tool.vercel] entrypoint` in pyproject.toml).

Vercel's Python runtime loads the top-level `app` variable and serves it.
"""

from __future__ import annotations

from src.adapters.webhook.app import app

__all__ = ["app"]

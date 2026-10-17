"""Application settings from environment (.env)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed config. Secrets come from env, never from code."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    customer_id: int
    executor_id: int
    database_url: str = "sqlite+aiosqlite:///./data/bot.db"
    log_level: str = "INFO"
    # Webhook mode (Vercel). Empty locally -> long polling fallback.
    webhook_base_url: str | None = None
    webhook_secret: str | None = None
    webhook_path: str = "/webhook"

    @property
    def allowed_user_ids(self) -> frozenset[int]:
        return frozenset({self.customer_id, self.executor_id})

    @property
    def webhook_url(self) -> str | None:
        """Public HTTPS webhook URL, or None when no base URL is configured."""
        if not self.webhook_base_url:
            return None
        return f"{self.webhook_base_url.rstrip('/')}/{self.webhook_path.lstrip('/')}"


def get_settings() -> Settings:
    return Settings()

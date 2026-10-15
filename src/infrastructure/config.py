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

    @property
    def allowed_user_ids(self) -> frozenset[int]:
        return frozenset({self.customer_id, self.executor_id})


def get_settings() -> Settings:
    return Settings()

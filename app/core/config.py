from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # --- общие ---
    env_name: str = Field("gpu-prod", alias="ENV_NAME")
    vds_hostname: str = Field("vds", alias="VDS_HOSTNAME")
    # --- Telegram (деплой) ---
    telegram_bot_token: str | None = Field(None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: int | None = Field(None, alias="TELEGRAM_CHAT_ID")

    # --- Telegram (транскрипции) ---
    transcribe_telegram_bot_token: str | None = Field(
        None, alias="TRANSCRIBE_TELEGRAM_BOT_TOKEN"
    )
    transcribe_telegram_chat_id: int | None = Field(
        None, alias="TRANSCRIBE_TELEGRAM_CHAT_ID"
    )

    # --- Telegram (model stat) ---
    all_eat_bot_token: str | None = Field(None, alias="OUR_ALL_EAT_TELEGRAM_BOT_TOKEN")
    all_eat_chat_id: str | None = Field(None, alias="OUR_ALL_EAT_TELEGRAM_CHAT_ID")

    # --- Postgres: используем единый URL ---
    database_url: str = Field(
        default="postgresql://postgres:123@localhost:5432/orchestrator",
        alias="DATABASE_URL",
    )

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def transcribe_telegram_enabled(self) -> bool:
        return bool(
            self.transcribe_telegram_bot_token and self.transcribe_telegram_chat_id
        )


settings = Settings()

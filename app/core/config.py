# app/core/config.py
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # говорить pydantic, что надо читать .env в корне проекта
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- общие ---
    env_name: str = Field("gpu-prod", alias="ENV_NAME")
    vds_hostname: str = Field("vds", alias="VDS_HOSTNAME")

    # --- лог ---
    deploy_log_path: str = Field("./data/deploy_log.jsonl", alias="DEPLOY_LOG_PATH")

    # --- GitHub ---
    github_webhook_secret: str = Field("", alias="GITHUB_WEBHOOK_SECRET")
    github_repo: str = Field("getyrno/ml-service-voice-trans", alias="GITHUB_REPO")

    # --- SSH до домашнего ПК ---
    home_ssh_user: str = Field("getyrno", alias="HOME_SSH_USER")
    home_ssh_host: str = Field("10.8.0.2", alias="HOME_SSH_HOST")
    home_ssh_key_path: str = Field("/root/.ssh/id_ed25519", alias="HOME_SSH_KEY_PATH")

    # --- healthcheck ---
    healthcheck_url: str = Field("http://10.8.0.2:8000/docs", alias="HEALTHCHECK_URL")

    # --- Telegram (для деплоев) ---
    telegram_bot_token: str | None = Field(None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: int | None = Field(None, alias="TELEGRAM_CHAT_ID")

    # --- Telegram (для транскрипций) ---
    transcribe_telegram_bot_token: str | None = Field(
        None, alias="TRANSCRIBE_TELEGRAM_BOT_TOKEN"
    )
    transcribe_telegram_chat_id: int | None = Field(
        None, alias="TRANSCRIBE_TELEGRAM_CHAT_ID"
    )

    # --- Postgres ---
    db_host: str = Field("db", alias="POSTGRES_HOST")
    db_port: int = Field(5432, alias="POSTGRES_PORT")
    db_name: str = Field("orch", alias="POSTGRES_DB")
    db_user: str = Field("orch", alias="POSTGRES_USER")
    db_password: str = Field("orchpass", alias="POSTGRES_PASSWORD")

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def transcribe_telegram_enabled(self) -> bool:
        return bool(
            self.transcribe_telegram_bot_token and self.transcribe_telegram_chat_id
        )


settings = Settings()

# app/core/config.py
from pydantic import BaseModel
import os
from dotenv import load_dotenv  # 👈 добавили

# загрузим .env из корня проекта (где main.py, requirements.txt и т.п.)
load_dotenv()


class Settings(BaseModel):
    # общие
    env_name: str = os.getenv("ENV_NAME", "gpu-prod")

    # лог
    deploy_log_path: str = os.getenv("DEPLOY_LOG_PATH", "./data/deploy_log.jsonl")

    # github
    github_webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    github_repo: str = os.getenv("GITHUB_REPO", "getyrno/ml-service-voice-trans")

    # ssh → домашний ПК
    home_ssh_user: str = os.getenv("HOME_SSH_USER", "getyrno")
    home_ssh_host: str = os.getenv("HOME_SSH_HOST", "10.8.0.2")
    home_ssh_key_path: str = os.getenv("HOME_SSH_KEY_PATH", "/keys/id_ed25519")

    # healthcheck
    healthcheck_url: str = os.getenv("HEALTHCHECK_URL", "http://10.8.0.2:8000/docs")

    # vds info
    vds_hostname: str = os.getenv("VDS_HOSTNAME", "vds")

    # Telegram
    # Telegram для транскрибаций (отдельный бот/чат)
    transcribe_telegram_bot_token: str = os.getenv("TRANSCRIBE_TELEGRAM_BOT_TOKEN", "")
    transcribe_telegram_chat_id: str = os.getenv("TRANSCRIBE_TELEGRAM_CHAT_ID", "")

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def transcribe_telegram_enabled(self) -> bool:
        return bool(self.transcribe_telegram_bot_token and self.transcribe_telegram_chat_id)
settings = Settings()

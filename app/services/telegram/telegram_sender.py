# app/services/telegram/telegram_sender.py
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


# Тип для файлов:
# files = {
#   "document": ("benchmark.png", png_bytes),
#   "document2": ("raw.json", json_bytes),
# }
TelegramFiles = Dict[str, Tuple[str, bytes]]


def send_telegram_message(
    token: Optional[str],
    chat_id: Optional[str],
    text: str,
    files: Optional[TelegramFiles] = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
) -> None:
    """
    Универсальный низкоуровневый отправитель сообщений в Telegram.

    - Если token или chat_id не переданы (None), используются all-eat настройки
      из ENV: OUR_ALL_EAT_TELEGRAM_BOT_TOKEN / OUR_ALL_EAT_TELEGRAM_CHAT_ID.
    - Если files=None -> используем sendMessage.
    - Если files есть -> отправляем первый файл как документ с caption=text.
      (Если нужно сложнее — можно поверх этого сделать отдельный helper.)

    Любые ошибки ЛОГИРУЮТСЯ, но НЕ пробрасываются выше — сервис не падает.
    """

    # Fallback к all-eat боту, если явно не передали
    if token is None:
        token = settings.all_eat_bot_token
    if chat_id is None:
        chat_id = settings.all_eat_chat_id

    if not token or not chat_id:
        logger.warning("Telegram sender disabled: no token/chat_id provided")
        return

    base_url = f"https://api.telegram.org/bot{token}"

    try:
        if not files:
            # Просто текст
            url = f"{base_url}/sendMessage"
            payload: Dict[str, Any] = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_web_page_preview,
            }
            resp = requests.post(url, json=payload, timeout=15)
        else:
            # Отправляем первый файл как документ с caption.
            # (остальные можно будет потом развить до sendMediaGroup)
            url = f"{base_url}/sendDocument"

            # Берём первый элемент из словаря
            field_name, (filename, content) = next(iter(files.items()))
            files_payload = {
                field_name: (filename, content),
            }

            data: Dict[str, Any] = {
                "chat_id": chat_id,
                "caption": text,
                "parse_mode": parse_mode,
            }

            resp = requests.post(
                url,
                data=data,
                files=files_payload,
                timeout=30,
            )

        if not resp.ok:
            logger.error(
                "Telegram send failed (%s): %s",
                resp.status_code,
                resp.text[:500],
            )
    except Exception:
        # Никаких raise — только лог.
        logger.exception("Telegram send exception")

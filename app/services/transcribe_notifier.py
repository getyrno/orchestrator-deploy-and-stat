# app/services/transcribe_notifier.py
from __future__ import annotations

from typing import Any
import textwrap

import requests

from app.core.config import settings
from app.schemas.transcribe import TranscribeEventIn


def _format_transcribe_message(ev: TranscribeEventIn) -> str:
    emoji = "🎧" if ev.success else "💥"

    filename = ev.filename or "-"
    size_mb = f"{(ev.filesize_bytes or 0) / (1024*1024):.2f} MB" if ev.filesize_bytes else "-"
    duration = f"{ev.duration_sec:.1f} s" if ev.duration_sec is not None else "-"

    latency = f"{ev.latency_ms} ms" if ev.latency_ms is not None else "-"
    t_ms = f"{ev.transcribe_ms} ms" if ev.transcribe_ms is not None else "-"
    f_ms = f"{ev.ffmpeg_ms} ms" if ev.ffmpeg_ms is not None else "-"

    lang = ev.language_detected or "-"
    model = ev.model_name or "-"
    device = ev.model_device or "-"

    client = ev.client or "-"
    err_code = ev.error_code or "-"
    err_msg = ev.error_message or "-"
    # 🤖 Model:   {model}
    # 💻 Device:  {device}
    # 🌐 Lang:    {lang}
    # 🎥 File:   {filename} 
    text = f"""
    {emoji} { 'SUCCESS' if ev.success else 'FAILED' } [{settings.env_name}]
    - Size: {size_mb} Length: {duration}
    - Длительность: {latency} Whisper: {t_ms} FFmpeg: {f_ms}
    [x] Error code: {err_code}
    [X] Error msg:  {err_msg}
    👤 Client: {client}
    """
    return textwrap.dedent(text).strip()


def send_transcribe_notification(ev: TranscribeEventIn) -> None:
    """
    Шлём уведомление о транскрибации во второго бота.
    Если токен/чат не настроены — тихо выходим.
    """
    if not settings.transcribe_telegram_enabled:
        return

    token = settings.transcribe_telegram_bot_token
    chat_id = settings.transcribe_telegram_chat_id

    text = _format_transcribe_message(ev)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }

    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code != 200:
            print(f"[transcribe-telegram] send failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[transcribe-telegram] exception while sending: {e}")

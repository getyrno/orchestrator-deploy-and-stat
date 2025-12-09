from __future__ import annotations

from typing import Any
import textwrap

import requests

from app.core.config import settings
from app.schemas.video_jobs import VideoJobEventIn, VideoJobStatus


def _format_video_job_message(ev: VideoJobEventIn) -> str:
    # эмодзи по статусу
    if ev.status == VideoJobStatus.DONE:
        emoji = "✅"
    elif ev.status == VideoJobStatus.FAIL:
        emoji = "❌"
    elif ev.status == VideoJobStatus.TIMEOUT:
        emoji = "⏰"
    elif ev.status == VideoJobStatus.IN_PROGRESS:
        emoji = "🔄"
    else:
        emoji = "🟡"  # STARTED / неизвестное

    job_id = str(ev.job_id)
    step = ev.step_code
    origin = ev.origin

    gpu_host = ev.gpu_host or "-"
    gpu_ver = ev.gpu_service_version or "-"
    model = ev.model_name or "-"
    model_ver = ev.model_version or "-"

    # тайминги
    if ev.step_duration_ms is not None:
        dur_ms = f"{ev.step_duration_ms} ms"
    elif ev.step_started_at_utc and ev.step_finished_at_utc:
        delta = ev.step_finished_at_utc - ev.step_started_at_utc
        dur_ms = f"{int(delta.total_seconds() * 1000)} ms"
    else:
        dur_ms = "-"

    msg = ev.message or "-"
    data_preview = "-"
    if ev.data:
        # маленький предпросмотр джейсона (обрежем, чтобы не раздувать сообщение)
        try:
            # просто str(ev.data) может быть длинным, поэтому режем
            s = str(ev.data)
            data_preview = (s[:400] + "…") if len(s) > 400 else s
        except Exception:
            data_preview = "<unserializable data>"

    text = f"""
    {emoji} VIDEO JOB [{settings.env_name}]
    🆔 Job:    {job_id}
    📌 Status: {ev.status.value}
    🧩 Step:   {step}
    📤 Origin: {origin}

    🖥 GPU host:   {gpu_host}
    🧱 GPU build:  {gpu_ver}
    🤖 Model:      {model}
    🧬 Model ver:  {model_ver}

    ⏱ Step time:   {dur_ms}

    📝 Message:
    {msg}

    🔍 Data:
    {data_preview}
    """
    return textwrap.dedent(text).strip()


def send_video_job_notification(ev: VideoJobEventIn) -> None:
    """
    Шлём уведомление в телеграм по видео-джобе.
    Чтобы не спамить, отсылаем ТОЛЬКО на финальные статусы:
    DONE / FAIL / TIMEOUT.
    Используем те же настройки, что и для transcribe-бота.
    """
    if not settings.transcribe_telegram_enabled:
        return

    # только финальные статусы
    # if ev.status not in (
    #     VideoJobStatus.DONE,
    #     VideoJobStatus.FAIL,
    #     VideoJobStatus.TIMEOUT,
    # ):
    #     return

    token = settings.transcribe_telegram_bot_token
    chat_id = settings.transcribe_telegram_chat_id

    if not token or not chat_id:
        return

    text = _format_video_job_message(ev)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        # parse_mode не ставим, чтобы не ловить ошибки форматирования
    }

    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code != 200:
            print(f"[video-job-telegram] send failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[video-job-telegram] exception while sending: {e}")

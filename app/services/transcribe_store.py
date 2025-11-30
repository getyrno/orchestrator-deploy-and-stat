# app/services/transcribe_store.py
from __future__ import annotations

import datetime as dt
import uuid

from app.core.config import settings
from app.services.db import get_conn
from app.schemas.transcribe import TranscribeEventIn


def save_transcribe_event(ev: TranscribeEventIn) -> None:
    """
    Сохраняет событие транскрибации в таблицу transcribe_events.
    created_at_utc и env проставляются на стороне оркестратора.
    """
    event_id = uuid.uuid4()
    now_utc = dt.datetime.now(dt.timezone.utc)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transcribe_events (
                    id,
                    created_at_utc,
                    env,
                    client,
                    client_ip,
                    request_id,
                    video_id,
                    filename,
                    filesize_bytes,
                    duration_sec,
                    content_type,
                    model_name,
                    model_device,
                    language_detected,
                    latency_ms,
                    transcribe_ms,
                    ffmpeg_ms,
                    success,
                    error_code,
                    error_message
                ) VALUES (
                    %(id)s,
                    %(created_at_utc)s,
                    %(env)s,
                    %(client)s,
                    %(client_ip)s,
                    %(request_id)s,
                    %(video_id)s,
                    %(filename)s,
                    %(filesize_bytes)s,
                    %(duration_sec)s,
                    %(content_type)s,
                    %(model_name)s,
                    %(model_device)s,
                    %(language_detected)s,
                    %(latency_ms)s,
                    %(transcribe_ms)s,
                    %(ffmpeg_ms)s,
                    %(success)s,
                    %(error_code)s,
                    %(error_message)s
                )
                """,
                {
                    "id": str(event_id),
                    "created_at_utc": now_utc,
                    "env": settings.env_name,

                    "client": ev.client,
                    "client_ip": ev.client_ip,

                    "request_id": ev.request_id,
                    "video_id": ev.video_id,
                    "filename": ev.filename,
                    "filesize_bytes": ev.filesize_bytes,
                    "duration_sec": ev.duration_sec,
                    "content_type": ev.content_type,
                    "model_name": ev.model_name,
                    "model_device": ev.model_device,
                    "language_detected": ev.language_detected,
                    "latency_ms": ev.latency_ms,
                    "transcribe_ms": ev.transcribe_ms,
                    "ffmpeg_ms": ev.ffmpeg_ms,
                    "success": ev.success,
                    "error_code": ev.error_code,
                    "error_message": ev.error_message,
                },
            )

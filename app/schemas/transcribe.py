# app/schemas/transcribe.py
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class TranscribeEventIn(BaseModel):
    """
    Событие, которое шлёт ML-сервис после транскрибации одного видео.
    """

    # идентификаторы
    request_id: str = Field(..., description="UUID или любой уникальный ID запроса")
    video_id: Optional[str] = None
    client: Optional[str] = None  # например, 'friend-1' или 'internal-tests'

    # инфо о входном файле
    filename: Optional[str] = None
    filesize_bytes: Optional[int] = None
    duration_sec: Optional[float] = None
    content_type: Optional[str] = None

    # модель
    model_name: Optional[str] = None      # whisper-base / small / medium / ...
    model_device: Optional[str] = None    # cuda / cpu
    language_detected: Optional[str] = None

    # производительность
    latency_ms: Optional[int] = None      # весь запрос
    transcribe_ms: Optional[int] = None   # чисто whisper
    ffmpeg_ms: Optional[int] = None       # извлечение аудио

    # статус
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None

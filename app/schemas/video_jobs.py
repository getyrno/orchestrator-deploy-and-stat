from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class VideoJobStatus(str, Enum):
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"


class VideoJobEventIn(BaseModel):
    """
    Событие от ML-сервиса про этап обработки одного видео.
    Этого достаточно, чтобы сложить всё в БД.
    """
    model_config = {
            "protected_namespaces": ()
        }
    # обязательное
    job_id: UUID
    step_code: str             # REQUEST_RECEIVED / FFMPEG_CONVERT / MODEL_INFERENCE / ...
    status: VideoJobStatus     # STARTED / IN_PROGRESS / DONE / FAIL / TIMEOUT

    # кто шлёт
    origin: str = "gpu"        # gpu / orchestrator / ...

    # инфа про gpu/модель (на будущее — кладём в video_jobs)
    gpu_host: str | None = None
    gpu_service_version: str | None = None
    model_name: str | None = None
    model_version: str | None = None

    # тайминги этапа (могут прилетать, могут нет)
    step_started_at_utc: datetime | None = None
    step_finished_at_utc: datetime | None = None
    step_duration_ms: int | None = None

    # человекочитаемый текст + произвольные метрики
    message: str | None = None
    data: dict[str, Any] | None = None

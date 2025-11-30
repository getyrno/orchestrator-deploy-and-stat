from __future__ import annotations

import datetime as dt
import json

from app.core.config import settings
from app.schemas.video_jobs import VideoJobEventIn
from app.services.db import get_conn


def save_video_job_event(ev: VideoJobEventIn) -> None:
    """
    Сохраняет событие видео-джобы:
    - создаёт запись в video_jobs, если её ещё нет
    - слегка обновляет общую инфу по job (статус, gpu, модель, тайминги)
    - пишет сырое событие в video_job_events
    """
    now_utc = dt.datetime.now(dt.timezone.utc)

    # если duration не прислали, но есть start/finish — досчитаем сами
    step_duration_ms: int | None = ev.step_duration_ms
    if step_duration_ms is None and ev.step_started_at_utc and ev.step_finished_at_utc:
        delta = ev.step_finished_at_utc - ev.step_started_at_utc
        step_duration_ms = int(delta.total_seconds() * 1000)

    with get_conn() as conn, conn.cursor() as cur:
        # 1) гарантируем, что job существует
        cur.execute(
            """
            INSERT INTO video_jobs (job_id, created_at_utc, env, status)
            VALUES (%s, %s, %s, %s::video_job_status)
            ON CONFLICT (job_id) DO NOTHING;
            """,
            (ev.job_id, now_utc, settings.env_name, ev.status.value),
        )

        # 2) слегка обновляем общую инфу по job
        cur.execute(
            """
            UPDATE video_jobs
            SET
                status              = %s::video_job_status,
                gpu_host            = COALESCE(gpu_host, %s),
                gpu_service_version = COALESCE(gpu_service_version, %s),
                model_name          = COALESCE(model_name, %s),
                model_version       = COALESCE(model_version, %s),
                started_at_utc      = COALESCE(started_at_utc, %s),
                finished_at_utc     = COALESCE(finished_at_utc, %s)
            WHERE job_id = %s;
            """,
            (
                ev.status.value,
                ev.gpu_host,
                ev.gpu_service_version,
                ev.model_name,
                ev.model_version,
                ev.step_started_at_utc,
                ev.step_finished_at_utc,
                ev.job_id,
            ),
        )

        # 3) если можно, считаем общую длительность job
        cur.execute(
            """
            UPDATE video_jobs
            SET duration_total_ms =
                CASE
                    WHEN started_at_utc IS NOT NULL
                         AND finished_at_utc IS NOT NULL
                         AND duration_total_ms IS NULL
                    THEN (EXTRACT(EPOCH FROM (finished_at_utc - started_at_utc)) * 1000)::int
                    ELSE duration_total_ms
                END
            WHERE job_id = %s;
            """,
            (ev.job_id,),
        )

        # 4) пишем само событие
        cur.execute(
            """
            INSERT INTO video_job_events (
                job_id,
                created_at_utc,
                env,
                origin,
                step_code,
                status,
                step_started_at_utc,
                step_finished_at_utc,
                step_duration_ms,
                message,
                data
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s::video_job_status,
                %s,
                %s,
                %s,
                %s,
                %s::jsonb
            );
            """,
            (
                ev.job_id,
                now_utc,
                settings.env_name,
                ev.origin,
                ev.step_code,
                ev.status.value,
                ev.step_started_at_utc,
                ev.step_finished_at_utc,
                step_duration_ms,
                ev.message,
                json.dumps(ev.data or {}),
            ),
        )

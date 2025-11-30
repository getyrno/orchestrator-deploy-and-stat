# app/services/migrations.py
from __future__ import annotations

import datetime as dt
import time
from typing import List, Dict

from app.services.db import get_conn

def wait_for_db(max_attempts: int = 10, delay_sec: int = 3) -> None:
    """
    Ждём, пока Postgres станет доступен.
    Пытаемся несколько раз сделать SELECT 1.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    _ = cur.fetchone()
            print("[migrations] DB is ready")
            return
        except Exception as e:
            print(f"[migrations] DB not ready (attempt {attempt}/{max_attempts}): {e}")
            time.sleep(delay_sec)
    raise RuntimeError("DB is not ready after retries")

# Список миграций в порядке применения
# version — уникальное имя (строка)
# sql — SQL-скрипт, который нужно выполнить
MIGRATIONS: List[Dict[str, str]] = [
    {
        "version": "0001_create_transcribe_events",
        "sql": """
        CREATE TABLE IF NOT EXISTS transcribe_events (
            id               uuid PRIMARY KEY,
            created_at_utc   timestamptz NOT NULL,
            env              text NOT NULL,
            client           text,

            request_id       text NOT NULL,
            video_id         text,

            filename         text,
            filesize_bytes   bigint,
            duration_sec     double precision,
            content_type     text,

            model_name       text,
            model_device     text,
            language_detected text,

            latency_ms       integer,
            transcribe_ms    integer,
            ffmpeg_ms        integer,

            success          boolean NOT NULL,
            error_code       text,
            error_message    text
        );

        CREATE INDEX IF NOT EXISTS idx_transcribe_events_created_at
            ON transcribe_events (created_at_utc);

        CREATE INDEX IF NOT EXISTS idx_transcribe_events_success
            ON transcribe_events (success);

        CREATE INDEX IF NOT EXISTS idx_transcribe_events_language
            ON transcribe_events (language_detected);
        """
    },
    {
        "version": "0002_add_client_ip",
        "sql": """
        ALTER TABLE transcribe_events
            ADD COLUMN client_ip text;

        CREATE INDEX IF NOT EXISTS idx_transcribe_events_client_ip
            ON transcribe_events (client_ip);
        """
    },
    {
        "version": "0003_create_video_jobs_and_events",
        "sql": """
        -- enum для статусов джоб/этапов
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'video_job_status'
            ) THEN
                CREATE TYPE video_job_status AS ENUM (
                    'STARTED', 'IN_PROGRESS', 'DONE', 'FAIL', 'TIMEOUT'
                );
            END IF;
        END
        $$;

        -- основная таблица видео-джоб
        CREATE TABLE IF NOT EXISTS video_jobs (
            job_id              uuid PRIMARY KEY,

            created_at_utc      timestamptz NOT NULL,
            env                 text        NOT NULL,

            status              video_job_status NOT NULL,

            -- базовая мета по запросу (на будущее)
            source              text,
            request_id          text,
            user_id             text,
            client_ip           text,

            -- gpu / модель (на будущее)
            gpu_host            text,
            gpu_service_version text,
            model_name          text,
            model_version       text,

            -- видео-мета (на будущее)
            video_source_type   text,
            video_original_name text,
            video_original_ext  text,
            video_mime          text,
            video_size_bytes    bigint,
            video_duration_sec  numeric(10,3),
            video_width         int,
            video_height        int,
            video_fps           numeric(10,3),
            video_video_codec   text,
            video_audio_codec   text,

            -- агрегированные тайминги (на будущее)
            started_at_utc      timestamptz,
            finished_at_utc     timestamptz,
            duration_total_ms   int,
            duration_convert_ms int,
            duration_inference_ms int,

            -- результат (на будущее)
            result_lang         text,
            result_segments     int,
            result_text_len     int,
            result_preview      text,
            result_storage_id   text,

            -- ошибки (на будущее)
            error_code          text,
            error_message       text,
            error_raw           jsonb
        );

        -- таблица событий по этапам пайплайна
        CREATE TABLE IF NOT EXISTS video_job_events (
            id                  bigserial PRIMARY KEY,
            job_id              uuid NOT NULL REFERENCES video_jobs(job_id) ON DELETE CASCADE,

            created_at_utc      timestamptz NOT NULL,
            env                 text        NOT NULL,

            origin              text        NOT NULL,  -- gpu / orchestrator / ...
            step_code           text        NOT NULL,  -- REQUEST_RECEIVED / FFMPEG_CONVERT / ...

            status              video_job_status NOT NULL,

            step_started_at_utc timestamptz,
            step_finished_at_utc timestamptz,
            step_duration_ms    int,

            message             text,
            data                jsonb
        );

        CREATE INDEX IF NOT EXISTS idx_video_job_events_job_id_created
            ON video_job_events (job_id, created_at_utc);

        CREATE INDEX IF NOT EXISTS idx_video_job_events_step_code
            ON video_job_events (step_code);

        CREATE INDEX IF NOT EXISTS idx_video_jobs_created_at
            ON video_jobs (created_at_utc);

        CREATE INDEX IF NOT EXISTS idx_video_jobs_status
            ON video_jobs (status);
        """
    }
]

def ensure_schema_migrations_table() -> None:
    """
    Создаём служебную таблицу для миграций, если её нет.
    """
    sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version     text PRIMARY KEY,
        applied_at  timestamptz NOT NULL DEFAULT now()
    );
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def get_applied_versions() -> set[str]:
    """
    Забираем уже применённые версии миграций.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations;")
            rows = cur.fetchall()
    return {row["version"] for row in rows}


def apply_migration(version: str, sql: str) -> None:
    """
    Применяем одну миграцию в транзакции и записываем её версию.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # start transaction (autocommit True, но psycopg сам начнёт транзакцию)
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (%s, %s);",
                (version, dt.datetime.now(dt.timezone.utc)),
            )


def apply_all_migrations() -> None:
    """
    Главная точка входа: создаём таблицу миграций,
    смотрим, что уже применено, и докатываем всё новое.
    """
    # ⬇⬇⬇ вот это добавили
    wait_for_db()

    ensure_schema_migrations_table()
    applied = get_applied_versions()

    for mig in MIGRATIONS:
        v = mig["version"]
        if v in applied:
            continue
        print(f"[migrations] applying {v} ...")
        apply_migration(v, mig["sql"])
        print(f"[migrations] {v} done")

# MIGRATIONS: List[Dict[str, str]] = [
#     {
#         "version": "0001_create_transcribe_events",
#         "sql": """ ... """
#     },
#     {
#         "version": "0002_add_client_version",
#         "sql": """
#         ALTER TABLE transcribe_events
#             ADD COLUMN client_version text;
#         """
#     },
# ]

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
    }
    # сюда потом добавим "0002_..." и т.д.
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

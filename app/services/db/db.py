# app/services/db.py
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
from app.core.config import settings


def get_conn():
    """
    Открываем новое подключение к Postgres
    через единый URL (DATABASE_URL).
    """
    conn = psycopg.connect(
        settings.database_url,
        autocommit=True,
        row_factory=dict_row,
    )
    return conn

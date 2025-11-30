# app/services/db.py
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


def get_conn():
    """
    Открываем новое подключение к Postgres.
    Для нашего объёма достаточно открывать коннект на операцию.
    """
    conn = psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        autocommit=True,
        row_factory=dict_row,
    )
    return conn

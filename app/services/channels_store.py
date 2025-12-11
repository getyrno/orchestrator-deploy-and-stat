from uuid import uuid4
from app.services.db.db import get_conn


def ensure_channel_exists(user_id: int, channel: str) -> str:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id FROM channels
            WHERE user_id = %s AND channel = %s AND is_active = TRUE;
        """, (user_id, channel))
        row = cur.fetchone()
        if row:
            return row["id"]

        new_id = str(uuid4())
        cur.execute("""
            INSERT INTO channels (id, user_id, channel)
            VALUES (%s, %s, %s);
        """, (new_id, user_id, channel))

        return new_id


def get_channels_by_user(user_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT * FROM channels
            WHERE user_id = %s
            ORDER BY created_at DESC;
        """, (user_id,))
        return cur.fetchall()


def deactivate_channel(channel_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE channels SET is_active = FALSE WHERE id = %s;
        """, (channel_id,))

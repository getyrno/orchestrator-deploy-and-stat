from app.services.db.db import get_conn

def ensure_user_exists(tg_id, username, first_name, last_name, language):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO users (tg_id, username, first_name, last_name, language_code)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (tg_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                language_code = EXCLUDED.language_code,
                updated_at = now();
        """, (tg_id, username, first_name, last_name, language))


def get_user_by_id(tg_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE tg_id = %s", (tg_id,))
        return cur.fetchone()

from alembic import op


# revision identifiers, used by Alembic.
revision = 'HASH'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS transcribe_events (
        id uuid PRIMARY KEY,
        created_at_utc timestamptz NOT NULL,
        env text NOT NULL,
        client text,
        request_id text NOT NULL,
        video_id text,
        filename text,
        filesize_bytes bigint,
        duration_sec double precision,
        content_type text,
        model_name text,
        model_device text,
        language_detected text,
        latency_ms integer,
        transcribe_ms integer,
        ffmpeg_ms integer,
        success boolean NOT NULL,
        error_code text,
        error_message text,
        client_ip text
    );
    """)

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_transcribe_events_created_at
        ON transcribe_events (created_at_utc);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS transcribe_events;")

"""create video_jobs and video_job_events

Revision ID: 9d4d8c8a71d6
Revises: 624a29ad635e
Create Date: 2025-12-11 04:04:33.011416
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9d4d8c8a71d6'
down_revision: Union[str, Sequence[str], None] = '624a29ad635e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUM type
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'video_job_status'
            ) THEN
                CREATE TYPE video_job_status AS ENUM (
                    'STARTED', 'IN_PROGRESS', 'DONE', 'FAIL', 'TIMEOUT'
                );
            END IF;
        END$$;
    """)

    # TABLE video_jobs
    op.execute("""
        CREATE TABLE video_jobs (
            job_id              uuid PRIMARY KEY,

            created_at_utc      timestamptz NOT NULL,
            env                 text        NOT NULL,

            status              video_job_status NOT NULL,

            -- new fields:
            user_id             BIGINT REFERENCES users(tg_id) ON DELETE SET NULL,
            channel_id          uuid REFERENCES channels(id) ON DELETE SET NULL,
            client_ip           text,

            gpu_host            text,
            gpu_service_version text,
            model_name          text,
            model_version       text,

            started_at_utc      timestamptz,
            finished_at_utc     timestamptz,
            duration_total_ms   int,
            duration_convert_ms int,
            duration_inference_ms int,

            source              text,
            request_id          text,

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

            result_lang         text,
            result_segments     int,
            result_text_len     int,
            result_preview      text,
            result_storage_id   text,

            error_code          text,
            error_message       text,
            error_raw           jsonb
        );
    """)

    # TABLE video_job_events
    op.execute("""
        CREATE TABLE video_job_events (
            id                      bigserial PRIMARY KEY,
            job_id                  uuid NOT NULL REFERENCES video_jobs(job_id) ON DELETE CASCADE,

            created_at_utc          timestamptz NOT NULL,
            env                     text NOT NULL,

            origin                  text NOT NULL,
            step_code               text NOT NULL,

            status                  video_job_status NOT NULL,

            step_started_at_utc     timestamptz,
            step_finished_at_utc    timestamptz,
            step_duration_ms        int,

            message                 text,
            data                    jsonb
        );
    """)

    # Indexes
    op.execute("CREATE INDEX idx_video_jobs_user_id ON video_jobs(user_id);")
    op.execute("CREATE INDEX idx_video_jobs_channel_id ON video_jobs(channel_id);")
    op.execute("CREATE INDEX idx_video_jobs_created_at ON video_jobs(created_at_utc);")

    op.execute("CREATE INDEX idx_video_job_events_job_id_created ON video_job_events(job_id, created_at_utc);")
    op.execute("CREATE INDEX idx_video_job_events_step_code ON video_job_events(step_code);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS video_job_events;")
    op.execute("DROP TABLE IF EXISTS video_jobs;")
    op.execute("DROP TYPE IF EXISTS video_job_status;")

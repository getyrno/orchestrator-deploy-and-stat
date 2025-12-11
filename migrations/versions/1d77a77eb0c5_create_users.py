from alembic import op

# revision identifiers, used by Alembic.
revision = '1d77a77eb0c5'
down_revision = 'HASH'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE users (
            tg_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            role TEXT NOT NULL DEFAULT 'user',
            is_banned BOOLEAN NOT NULL DEFAULT FALSE
        );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS users;")

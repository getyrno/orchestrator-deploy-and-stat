"""create channels table

Revision ID: 624a29ad635e
Revises: 1d77a77eb0c5
Create Date: 2025-12-11 04:02:46.857105

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '624a29ad635e'
down_revision: Union[str, Sequence[str], None] = '1d77a77eb0c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("""
        CREATE TABLE channels (
            id uuid PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
            channel TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS channels;
    """)

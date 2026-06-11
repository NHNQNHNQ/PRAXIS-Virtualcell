"""spawn_tasks 表: 异步 LLM 任务 + 单 user 索引。

Revision ID: 004_spawn_tasks
Revises: 003_files
"""

from __future__ import annotations

from alembic import op

revision = "004_spawn_tasks"
down_revision = "003_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE spawn_tasks (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            prompt        TEXT NOT NULL,
            model         TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','running','done','failed','cancelled')),
            answer        TEXT NOT NULL DEFAULT '',
            tokens_in     INTEGER NOT NULL DEFAULT 0 CHECK (tokens_in >= 0),
            tokens_out    INTEGER NOT NULL DEFAULT 0 CHECK (tokens_out >= 0),
            cost_li       BIGINT NOT NULL DEFAULT 0 CHECK (cost_li >= 0),
            error         TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            started_at    TIMESTAMPTZ,
            completed_at  TIMESTAMPTZ
        );
    """)
    op.execute(
        "CREATE INDEX ix_spawn_tasks_user_created "
        "ON spawn_tasks(user_id, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_spawn_tasks_user_created;")
    op.execute("DROP TABLE IF EXISTS spawn_tasks;")

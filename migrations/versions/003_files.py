"""files 表: 用户上传文件元数据 + 2 个 partial index。

Revision ID: 003_files
Revises: 002_user_profile_billing
"""

from __future__ import annotations

from alembic import op

revision = "003_files"
down_revision = "002_user_profile_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE files (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename    TEXT NOT NULL,
            size_bytes  BIGINT NOT NULL CHECK (size_bytes >= 0),
            mime        TEXT,
            purpose     TEXT NOT NULL
                          CHECK (purpose IN ('pdb','config','report','md_input','other')),
            storage_key TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ
        );
    """)
    op.execute(
        "CREATE INDEX ix_files_user_purpose "
        "ON files(user_id, purpose) WHERE deleted_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX ix_files_user_created "
        "ON files(user_id, created_at DESC) WHERE deleted_at IS NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_files_user_created;")
    op.execute("DROP INDEX IF EXISTS ix_files_user_purpose;")
    op.execute("DROP TABLE IF EXISTS files;")

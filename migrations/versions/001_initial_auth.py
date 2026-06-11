"""initial auth schema: users + email_codes + audit_log + pgcrypto.

Revision ID: 001_initial_auth
Revises: (initial)
"""

from __future__ import annotations

from alembic import op

revision = "001_initial_auth"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.execute("""
        CREATE TABLE users (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email                VARCHAR(255) NOT NULL,
            phone                VARCHAR(20),
            password_hash        BYTEA NOT NULL,
            display_name         VARCHAR(64),
            role                 VARCHAR(16) NOT NULL DEFAULT 'user',
            plan                 VARCHAR(16) NOT NULL DEFAULT 'free',
            status               VARCHAR(16) NOT NULL DEFAULT 'active',
            balance_li           BIGINT      NOT NULL DEFAULT 0,
            realname_verified_at TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_login_at        TIMESTAMPTZ,
            last_login_ip        INET,
            deleted_at           TIMESTAMPTZ
        );
    """)
    op.execute("CREATE UNIQUE INDEX uq_users_email ON users (email) WHERE deleted_at IS NULL;")
    op.execute("CREATE INDEX ix_users_phone ON users (phone) WHERE phone IS NOT NULL;")

    op.execute("""
        CREATE TABLE email_codes (
            id          BIGSERIAL PRIMARY KEY,
            email       VARCHAR(255) NOT NULL,
            code        VARCHAR(10)  NOT NULL,
            purpose     VARCHAR(16)  NOT NULL,
            attempts    INTEGER      NOT NULL DEFAULT 0,
            used        BOOLEAN      NOT NULL DEFAULT FALSE,
            expires_at  TIMESTAMPTZ  NOT NULL,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_email_codes_email_created ON email_codes (email, created_at DESC);")

    op.execute("""
        CREATE TABLE audit_log (
            id          BIGSERIAL PRIMARY KEY,
            user_id     UUID,
            actor       VARCHAR(64) NOT NULL,
            action      VARCHAR(48) NOT NULL,
            resource    VARCHAR(48),
            resource_id VARCHAR(64),
            ip          INET,
            ua          TEXT,
            meta        JSONB,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_audit_user_created ON audit_log (user_id, created_at DESC);")
    op.execute("CREATE INDEX ix_audit_action_created ON audit_log (action, created_at DESC);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log;")
    op.execute("DROP TABLE IF EXISTS email_codes;")
    op.execute("DROP TABLE IF EXISTS users;")
    # pgcrypto 不 drop(其他 db 可能用)

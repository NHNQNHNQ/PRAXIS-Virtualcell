"""user_profiles + ledger.

Revision ID: 002_user_profile_billing
Revises: 001_initial_auth
"""

from __future__ import annotations

from alembic import op

revision = "002_user_profile_billing"
down_revision = "001_initial_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_profiles (
            user_id         UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            research_field  VARCHAR(256),
            affiliation     VARCHAR(256),
            expertise_level VARCHAR(256),
            projects        VARCHAR(2000),
            custom_intro    VARCHAR(2000),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE TABLE ledger (
            id            BIGSERIAL PRIMARY KEY,
            user_id       UUID         NOT NULL REFERENCES users(id),
            amount_li     BIGINT       NOT NULL,
            kind          VARCHAR(32)  NOT NULL,
            ref_type      VARCHAR(32),
            ref_id        VARCHAR(64),
            balance_after BIGINT       NOT NULL,
            meta          JSONB,
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
        );
    """)
    op.execute(
        "CREATE INDEX ix_ledger_user_created ON ledger(user_id, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ledger_user_created;")
    op.execute("DROP TABLE IF EXISTS ledger;")
    op.execute("DROP TABLE IF EXISTS user_profiles;")

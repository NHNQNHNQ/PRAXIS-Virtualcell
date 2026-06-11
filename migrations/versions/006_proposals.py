"""proposals 表: 用户 idea/feature/bug + admin 决策审计。

Revision ID: 006_proposals
Revises: 005_md_jobs
"""

from __future__ import annotations

from alembic import op

revision = "006_proposals"
down_revision = "005_md_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE proposals (
          id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          kind          TEXT NOT NULL CHECK (kind IN ('idea','feature','bug')),
          title         TEXT NOT NULL,
          body          TEXT,
          status        TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','decided','closed')),
          state         TEXT NOT NULL DEFAULT 'submitted'
                        CHECK (state IN ('submitted','withdrawn','archived')),
          admin_verdict TEXT CHECK (admin_verdict IN ('ship','promote','hold','reject')),
          admin_scores  JSONB,
          shipped_to    TEXT,
          decision_note TEXT,
          decided_at    TIMESTAMPTZ,
          decided_by    UUID REFERENCES users(id) ON DELETE SET NULL,
          created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute(
        "CREATE INDEX ix_proposals_user_created ON proposals (user_id, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX ix_proposals_status_created ON proposals (status, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_proposals_status_created;")
    op.execute("DROP INDEX IF EXISTS ix_proposals_user_created;")
    op.execute("DROP TABLE IF EXISTS proposals;")

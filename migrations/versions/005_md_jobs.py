"""md_jobs 表: GROMACS MD 异步作业 + 2 个 index。

Revision ID: 005_md_jobs
Revises: 004_spawn_tasks
"""

from __future__ import annotations

from alembic import op

revision = "005_md_jobs"
down_revision = "004_spawn_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE md_jobs (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            sim_type      TEXT NOT NULL
                            CHECK (sim_type IN ('standard','smd_pulling','metadynamics')),
            params        JSONB NOT NULL,
            status        TEXT NOT NULL DEFAULT 'queued'
                            CHECK (status IN ('queued','running','done','failed','cancelled')),
            slurm_job_id  TEXT,
            gpu_host      TEXT,
            progress      INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
            error         TEXT,
            cost_li       BIGINT NOT NULL DEFAULT 0 CHECK (cost_li >= 0),
            cpu_hours     NUMERIC(10,3) NOT NULL DEFAULT 0,
            gpu_hours     NUMERIC(10,3) NOT NULL DEFAULT 0,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            started_at    TIMESTAMPTZ,
            finished_at   TIMESTAMPTZ
        );
    """)
    op.execute(
        "CREATE INDEX ix_md_jobs_user_created "
        "ON md_jobs(user_id, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX ix_md_jobs_active_status "
        "ON md_jobs(status) WHERE status IN ('queued','running');"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_md_jobs_active_status;")
    op.execute("DROP INDEX IF EXISTS ix_md_jobs_user_created;")
    op.execute("DROP TABLE IF EXISTS md_jobs;")

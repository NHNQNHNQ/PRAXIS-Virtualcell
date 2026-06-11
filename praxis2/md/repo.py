"""md_jobs 表 CRUD + finalize 接 ledger 同事务。"""
from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg


class MdJobRepo:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self, conn: asyncpg.Connection,
        user_id: str, sim_type: str, params: dict,
    ) -> str:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        row = await conn.fetchrow(
            "INSERT INTO md_jobs (user_id, sim_type, params) "
            "VALUES ($1, $2, $3::jsonb) RETURNING id",
            uid, sim_type, json.dumps(params),
        )
        return str(row["id"])

    async def get(self, job_id: str) -> dict[str, Any] | None:
        jid = uuid.UUID(job_id)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(_SELECT + " WHERE id=$1", jid)
        return _row_to_dict(row) if row else None

    async def list_recent(self, user_id: str, limit: int = 100) -> list[dict]:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                _SELECT + " WHERE user_id=$1 ORDER BY created_at DESC LIMIT $2",
                uid, int(limit),
            )
        return [_row_to_dict(r) for r in rows]

    async def list_active(self) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                _SELECT + " WHERE status IN ('queued','running') "
                "ORDER BY created_at ASC",
            )
        return [_row_to_dict(r) for r in rows]

    async def count_active(self, user_id: str) -> int:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT count(*) FROM md_jobs "
                "WHERE user_id=$1 AND status IN ('queued','running')",
                uid,
            )

    async def update_submitted(self, job_id: str, *, slurm_job_id: str) -> None:
        jid = uuid.UUID(job_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE md_jobs SET slurm_job_id=$2 WHERE id=$1",
                jid, slurm_job_id,
            )

    async def update_status(
        self, job_id: str, status: str, *, gpu_host: str | None = None,
    ) -> None:
        jid = uuid.UUID(job_id)
        async with self._pool.acquire() as conn:
            if status == "running":
                await conn.execute(
                    "UPDATE md_jobs SET status='running', started_at=now(), "
                    "gpu_host=COALESCE($2, gpu_host) "
                    "WHERE id=$1 AND status='queued'",
                    jid, gpu_host,
                )
            else:
                await conn.execute(
                    "UPDATE md_jobs SET status=$2 WHERE id=$1",
                    jid, status,
                )

    async def update_cancelled(self, job_id: str) -> None:
        jid = uuid.UUID(job_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE md_jobs SET status='cancelled', finished_at=now() "
                "WHERE id=$1 AND status IN ('queued','running')",
                jid,
            )

    async def finalize(
        self, conn: asyncpg.Connection,
        job_id: str, *, status: str,
        cpu_hours: float, gpu_hours: float, cost_li: int,
        error: str | None,
    ) -> None:
        """终态写入 — 必须在调用方事务里(ledger.record 同事务)。"""
        jid = uuid.UUID(job_id)
        await conn.execute(
            "UPDATE md_jobs SET status=$2, cpu_hours=$3, gpu_hours=$4, "
            "cost_li=$5, error=$6, finished_at=now() WHERE id=$1",
            jid, status, float(cpu_hours), float(gpu_hours),
            int(cost_li), (error or None),
        )


_SELECT = (
    "SELECT id, user_id, sim_type, params, status, slurm_job_id, "
    "       gpu_host, progress, error, cost_li, "
    "       cpu_hours, gpu_hours, "
    "       created_at, started_at, finished_at "
    "FROM md_jobs"
)


def _row_to_dict(r) -> dict[str, Any]:
    p = r["params"]
    if isinstance(p, str):
        p = json.loads(p)
    return {
        "id": str(r["id"]),
        "user_id": str(r["user_id"]),
        "sim_type": r["sim_type"],
        "params": p,
        "status": r["status"],
        "slurm_job_id": r["slurm_job_id"],
        "gpu_host": r["gpu_host"],
        "progress": int(r["progress"]),
        "error": r["error"],
        "cost_li": int(r["cost_li"]),
        "cpu_hours": float(r["cpu_hours"]),
        "gpu_hours": float(r["gpu_hours"]),
        "created_at": r["created_at"],
        "started_at": r["started_at"],
        "finished_at": r["finished_at"],
    }

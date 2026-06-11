"""spawn_tasks 表 CRUD。

写路径:create / update_* 需调用方传 conn(便于跟 ledger 同事务);
读路径:get / list_recent / count_active 自取连接。
"""
from __future__ import annotations

import uuid
from typing import Any

import asyncpg


class SpawnRepo:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self, conn: asyncpg.Connection,
        user_id: str, prompt: str, model: str,
    ) -> str:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        row = await conn.fetchrow(
            "INSERT INTO spawn_tasks (user_id, prompt, model) "
            "VALUES ($1, $2, $3) RETURNING id",
            uid, prompt, model,
        )
        return str(row["id"])

    async def get(self, task_id: str) -> dict[str, Any] | None:
        tid = uuid.UUID(task_id)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, user_id, prompt, model, status, answer, "
                "       tokens_in, tokens_out, cost_li, error, "
                "       created_at, started_at, completed_at "
                "FROM spawn_tasks WHERE id=$1", tid,
            )
        return _row_to_dict(row) if row else None

    async def list_recent(self, user_id: str, limit: int = 100) -> list[dict]:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, user_id, prompt, model, status, answer, "
                "       tokens_in, tokens_out, cost_li, error, "
                "       created_at, started_at, completed_at "
                "FROM spawn_tasks WHERE user_id=$1 "
                "ORDER BY created_at DESC LIMIT $2",
                uid, int(limit),
            )
        return [_row_to_dict(r) for r in rows]

    async def count_active(self, user_id: str) -> int:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT count(*) FROM spawn_tasks "
                "WHERE user_id=$1 AND status IN ('pending','running')",
                uid,
            )

    async def update_running(self, task_id: str) -> None:
        tid = uuid.UUID(task_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE spawn_tasks SET status='running', started_at=now() "
                "WHERE id=$1", tid,
            )

    async def update_partial(self, task_id: str, answer_so_far: str) -> None:
        tid = uuid.UUID(task_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE spawn_tasks SET answer=$2 WHERE id=$1",
                tid, answer_so_far,
            )

    async def update_done(
        self, conn: asyncpg.Connection,
        task_id: str, answer: str,
        tokens_in: int, tokens_out: int, cost_li: int,
    ) -> None:
        tid = uuid.UUID(task_id)
        await conn.execute(
            "UPDATE spawn_tasks SET status='done', answer=$2, "
            "tokens_in=$3, tokens_out=$4, cost_li=$5, completed_at=now() "
            "WHERE id=$1",
            tid, answer, int(tokens_in), int(tokens_out), int(cost_li),
        )

    async def update_failed(self, task_id: str, error_msg: str) -> None:
        tid = uuid.UUID(task_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE spawn_tasks SET status='failed', error=$2, "
                "completed_at=now() WHERE id=$1",
                tid, error_msg[:2000],
            )

    async def update_cancelled(self, task_id: str) -> None:
        tid = uuid.UUID(task_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE spawn_tasks SET status='cancelled', completed_at=now() "
                "WHERE id=$1", tid,
            )

    async def trim_old(self, user_id: str, keep: int = 100) -> int:
        """删超出 keep 条之外的老任务。返回删除行数。"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM spawn_tasks WHERE id IN ("
                "  SELECT id FROM spawn_tasks WHERE user_id=$1 "
                "  ORDER BY created_at DESC OFFSET $2"
                ")",
                uid, int(keep),
            )
        # asyncpg execute 返回 "DELETE N" 格式的 command tag
        return int(result.split()[-1]) if result else 0


def _row_to_dict(r) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "user_id": str(r["user_id"]),
        "prompt": r["prompt"],
        "model": r["model"],
        "status": r["status"],
        "answer": r["answer"],
        "tokens_in": int(r["tokens_in"]),
        "tokens_out": int(r["tokens_out"]),
        "cost_li": int(r["cost_li"]),
        "error": r["error"],
        "created_at": r["created_at"],
        "started_at": r["started_at"],
        "completed_at": r["completed_at"],
    }

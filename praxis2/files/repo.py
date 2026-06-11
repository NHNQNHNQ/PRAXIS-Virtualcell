"""FilesRepo:asyncpg CRUD against `files` 表。"""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg


class FilesRepo:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_file(
        self,
        *,
        user_id: str,
        filename: str,
        size_bytes: int,
        mime: str | None,
        purpose: str,
        storage_key: str,
    ) -> dict[str, Any]:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO files
                       (user_id, filename, size_bytes, mime, purpose, storage_key)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   RETURNING id, filename, size_bytes, mime, purpose,
                             storage_key, created_at""",
                uid, filename, int(size_bytes), mime, purpose, storage_key,
            )
        return _row_to_dict(row)

    async def list_files(
        self, *, user_id: str, purpose: str | None,
    ) -> list[dict[str, Any]]:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        if purpose is None:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT id, filename, size_bytes, mime, purpose,
                              storage_key, created_at FROM files
                       WHERE user_id=$1 AND deleted_at IS NULL
                       ORDER BY created_at DESC""",
                    uid,
                )
        else:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT id, filename, size_bytes, mime, purpose,
                              storage_key, created_at FROM files
                       WHERE user_id=$1 AND purpose=$2 AND deleted_at IS NULL
                       ORDER BY created_at DESC""",
                    uid, purpose,
                )
        return [_row_to_dict(r) for r in rows]

    async def get(self, file_id: str) -> dict[str, Any] | None:
        """按 file_id 查(不做 user_id 过滤,调用方自行校验归属)。"""
        try:
            fid = uuid.UUID(file_id) if isinstance(file_id, str) else file_id
        except ValueError:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, user_id, filename, size_bytes, mime, purpose,
                          storage_key, created_at FROM files
                   WHERE id=$1 AND deleted_at IS NULL""",
                fid,
            )
        if row is None:
            return None
        d = _row_to_dict(row)
        d["user_id"] = str(row["user_id"])
        return d

    async def get_file(
        self, *, user_id: str, file_id: str,
    ) -> dict[str, Any] | None:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        try:
            fid = uuid.UUID(file_id) if isinstance(file_id, str) else file_id
        except ValueError:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, filename, size_bytes, mime, purpose,
                          storage_key, created_at FROM files
                   WHERE id=$1 AND user_id=$2 AND deleted_at IS NULL""",
                fid, uid,
            )
        return _row_to_dict(row) if row else None

    async def soft_delete(
        self, *, user_id: str, file_id: str,
    ) -> str | None:
        """返被删的 file_id;不归属当前用户 / 已删 → None。"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        try:
            fid = uuid.UUID(file_id) if isinstance(file_id, str) else file_id
        except ValueError:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE files SET deleted_at=now()
                   WHERE id=$1 AND user_id=$2 AND deleted_at IS NULL
                   RETURNING id""",
                fid, uid,
            )
        return str(row["id"]) if row else None

    async def usage(self, *, user_id: str) -> dict[str, int]:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT COALESCE(SUM(size_bytes), 0) AS used_bytes,
                          COUNT(*) AS cnt
                   FROM files WHERE user_id=$1 AND deleted_at IS NULL""",
                uid,
            )
        return {"used_bytes": int(row["used_bytes"]), "count": int(row["cnt"])}


def _row_to_dict(r) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "filename": r["filename"],
        "size_bytes": int(r["size_bytes"]),
        "mime": r["mime"],
        "purpose": r["purpose"],
        "storage_key": r["storage_key"],
        "created_at": r["created_at"],
    }

"""PgStore 真后端实现(v1.1 carry ① 关闭,§11.4)。

通用 KV → praxis_store(JSONB + ttl_at);Blob → praxis_blob(BYTEA);
Meta → praxis_meta(table_name + user_id + pk → JSONB row)。
启动期 make_pg_pool 自动建三表(idempotent,M9 不依赖 alembic 单独 migration)。
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

import asyncpg

from praxis2.store.base import Namespace, Store

_STORE_DDL = """
CREATE TABLE IF NOT EXISTS praxis_store (
    user_id TEXT NOT NULL, scope TEXT NOT NULL, key TEXT NOT NULL,
    value JSONB NOT NULL, ttl_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, scope, key)
);
CREATE TABLE IF NOT EXISTS praxis_blob (
    user_id TEXT NOT NULL, scope TEXT NOT NULL, key TEXT NOT NULL,
    data BYTEA NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, scope, key)
);
CREATE TABLE IF NOT EXISTS praxis_meta (
    table_name TEXT NOT NULL, user_id TEXT NOT NULL, pk TEXT NOT NULL,
    row JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (table_name, user_id, pk)
);
"""


async def make_pg_pool(url: str, **kwargs) -> asyncpg.Pool:
    """asyncpg pool 工厂(统一所有 PG 访问入口,auth/store 共享)。"""
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://") :]
    pool = await asyncpg.create_pool(dsn=url, **kwargs)
    async with pool.acquire() as conn:
        await conn.execute(_STORE_DDL)
    return pool


class PgStore(Store):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def kv_set(
        self, ns: Namespace, key: str, value: bytes, ttl_s: float | None = None
    ) -> None:
        ttl_at = None
        if ttl_s is not None:
            ttl_at = datetime.fromtimestamp(datetime.now(UTC).timestamp() + ttl_s, tz=UTC)
        wrapped = json.dumps({"__b64__": base64.b64encode(value).decode()})
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO praxis_store (user_id, scope, key, value, ttl_at)
                   VALUES ($1, $2, $3, $4::jsonb, $5)
                   ON CONFLICT (user_id, scope, key) DO UPDATE
                   SET value = EXCLUDED.value, ttl_at = EXCLUDED.ttl_at""",
                ns.user_id,
                ns.scope,
                key,
                wrapped,
                ttl_at,
            )

    async def kv_get(self, ns: Namespace, key: str) -> bytes | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT value, ttl_at FROM praxis_store
                   WHERE user_id=$1 AND scope=$2 AND key=$3""",
                ns.user_id,
                ns.scope,
                key,
            )
        if not row:
            return None
        if row["ttl_at"] and row["ttl_at"] < datetime.now(UTC):
            await self.kv_delete(ns, key)
            return None
        v = json.loads(row["value"])
        return base64.b64decode(v["__b64__"]) if "__b64__" in v else json.dumps(v).encode()

    async def kv_delete(self, ns: Namespace, key: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM praxis_store WHERE user_id=$1 AND scope=$2 AND key=$3",
                ns.user_id,
                ns.scope,
                key,
            )

    async def blob_put(self, ns: Namespace, key: str, data: bytes) -> str:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO praxis_blob (user_id, scope, key, data)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (user_id, scope, key) DO UPDATE SET data = EXCLUDED.data""",
                ns.user_id,
                ns.scope,
                key,
                data,
            )
        return key

    async def blob_get(self, ns: Namespace, key: str) -> bytes | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM praxis_blob WHERE user_id=$1 AND scope=$2 AND key=$3",
                ns.user_id,
                ns.scope,
                key,
            )
        return row["data"] if row else None

    async def blob_append(self, ns: Namespace, key: str, chunk: bytes) -> None:
        """原子追加(单条 SQL):INSERT ON CONFLICT DO UPDATE 拼接 bytea。

        PG 的 || 操作符对 bytea 是字节级拼接;整个 UPSERT 在单语句内
        持行锁,并发追加同一 (user_id, scope, key) 不会丢条。
        反 read-modify-write:不读旧值,不重写整盘 → O(1) 单条追加。
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO praxis_blob (user_id, scope, key, data)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (user_id, scope, key) DO UPDATE
                   SET data = praxis_blob.data || EXCLUDED.data""",
                ns.user_id,
                ns.scope,
                key,
                chunk,
            )

    async def meta_upsert(self, table: str, row: dict) -> None:
        user_id = row.get("user_id") or ""
        pk = row.get("id") or row.get("pk") or ""
        if not user_id or not pk:
            raise ValueError("meta_upsert row 需含 user_id + id/pk")
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO praxis_meta (table_name, user_id, pk, row)
                   VALUES ($1, $2, $3, $4::jsonb)
                   ON CONFLICT (table_name, user_id, pk) DO UPDATE
                   SET row = EXCLUDED.row""",
                table,
                user_id,
                pk,
                json.dumps(row),
            )

    async def meta_get(self, table: str, user_id: str, pk: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT row FROM praxis_meta
                   WHERE table_name=$1 AND user_id=$2 AND pk=$3""",
                table,
                user_id,
                pk,
            )
        return json.loads(row["row"]) if row else None

    async def meta_list(self, table: str, user_id: str) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT row FROM praxis_meta
                   WHERE table_name=$1 AND user_id=$2
                   ORDER BY created_at""",
                table,
                user_id,
            )
        return [json.loads(r["row"]) for r in rows]

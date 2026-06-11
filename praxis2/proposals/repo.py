"""proposals 表 CRUD + decide 接 audit_log 同事务。"""
from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg

_PROPOSAL_KIND = {"idea", "feature", "bug"}
_PROPOSAL_VERDICT = {"ship", "promote", "hold", "reject"}


def _derive_display_status(
    status: str | None,
    verdict: str | None,
    shipped_to: str | None,
) -> str:
    """Carry(2026-05-31):FE STATUS_LABEL = pending/shipped/promoted/held/rejected,
    后端 (status, admin_verdict, shipped_to) 二元组 → 这里 derive 统一展示态。

    映射:
      open                            → pending
      decided + ship + shipped_to≠∅   → promoted(canonical 二段动作)
      decided + ship + null           → shipped
      decided + hold                  → held
      decided + reject                → rejected
      其他未预期组合                  → pending(保守 fallback,FE 走 KEY 命中)
    """
    if status == "open":
        return "pending"
    if status == "decided":
        if verdict == "ship":
            return "promoted" if shipped_to else "shipped"
        if verdict == "hold":
            return "held"
        if verdict == "reject":
            return "rejected"
    return "pending"


class ProposalRepo:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self, conn: asyncpg.Connection,
        user_id: str, kind: str, title: str, body: str | None,
    ) -> str:
        if kind not in _PROPOSAL_KIND:
            raise ValueError(f"invalid_kind:{kind}")
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        row = await conn.fetchrow(
            "INSERT INTO proposals (user_id, kind, title, body) "
            "VALUES ($1, $2, $3, $4) RETURNING id, status, state, created_at",
            uid, kind, title, body,
        )
        return str(row["id"])

    async def list_mine(
        self, user_id: str, page: int, limit: int,
    ) -> dict[str, Any]:
        """user 列表 (page+limit). 故意不 SELECT admin_scores: 内部评分不暴露给 user."""
        uid = uuid.UUID(user_id)
        offset = (page - 1) * limit
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, kind, title, body, status, state, admin_verdict, "
                "shipped_to, decision_note, decided_at, created_at "
                "FROM proposals WHERE user_id=$1 "
                "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                uid, limit, offset,
            )
            total = await conn.fetchval(
                "SELECT count(*) FROM proposals WHERE user_id=$1", uid,
            )
        return {
            "rows": [self._row_to_dict(r) for r in rows],
            "total": int(total),
            "page": page,
            "limit": limit,
        }

    async def count_recent(self, user_id: str, hours: int = 24) -> int:
        """rate limit 用:user 最近 N 小时 proposal 数。"""
        uid = uuid.UUID(user_id)
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT count(*) FROM proposals "
                "WHERE user_id=$1 AND created_at > now() - ($2 || ' hours')::interval",
                uid, str(hours),
            )
        return int(result or 0)

    async def list_all(
        self, filters: dict[str, Any], page: int, limit: int,
    ) -> dict[str, Any]:
        """admin 用:全表 + 可选 status/kind filter。"""
        offset = (page - 1) * limit
        where_clauses = []
        args: list[Any] = []
        if filters.get("status"):
            args.append(filters["status"])
            where_clauses.append(f"status = ${len(args)}")
        if filters.get("kind"):
            args.append(filters["kind"])
            where_clauses.append(f"kind = ${len(args)}")
        where_sql = (
            " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        )
        args.extend([limit, offset])
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT id, user_id, kind, title, body, status, state, "
                f"admin_verdict, admin_scores, shipped_to, decision_note, "
                f"decided_at, decided_by, created_at "
                f"FROM proposals{where_sql} "
                f"ORDER BY created_at DESC LIMIT ${len(args)-1} OFFSET ${len(args)}",
                *args,
            )
            total = await conn.fetchval(
                f"SELECT count(*) FROM proposals{where_sql}",
                *args[:-2],
            )
        return {
            "rows": [self._admin_row_to_dict(r) for r in rows],
            "total": int(total),
            "page": page,
            "limit": limit,
        }

    async def decide(
        self, conn: asyncpg.Connection,
        proposal_id: str, admin_id: str, verdict: str,
        score: int | None = None,
        shipped_to: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """admin 决策。caller 提供 conn(同 tx 跟 audit 一起 commit)。

        返 dict {ok, status, verdict, decided_at};
        若 status != 'open' 抛 ProposalAlreadyDecided;row 不存在抛 ProposalNotFound。
        """
        if verdict not in _PROPOSAL_VERDICT:
            raise ValueError(f"invalid_verdict:{verdict}")
        if score is not None and not (1 <= score <= 5):
            raise ValueError(f"invalid_score:{score}")
        pid = uuid.UUID(proposal_id)
        aid = uuid.UUID(admin_id)

        # 检查 status 必 open
        cur = await conn.fetchrow(
            "SELECT status FROM proposals WHERE id=$1 FOR UPDATE", pid,
        )
        if cur is None:
            raise ProposalNotFound(proposal_id)
        if cur["status"] != "open":
            raise ProposalAlreadyDecided(proposal_id, cur["status"])

        # admin_scores jsonb_set 累加
        scores_arg = (
            json.dumps(score) if score is not None else None
        )
        row = await conn.fetchrow(
            """
            UPDATE proposals SET
              status='decided',
              admin_verdict=$2,
              admin_scores=CASE
                WHEN $3::jsonb IS NULL THEN admin_scores
                ELSE jsonb_set(
                  COALESCE(admin_scores, '{}'::jsonb),
                  ARRAY[$4::text],
                  $3::jsonb
                )
              END,
              shipped_to=$5,
              decision_note=$6,
              decided_at=now(),
              decided_by=$7
            WHERE id=$1
            RETURNING status, admin_verdict, decided_at
            """,
            pid, verdict, scores_arg, str(aid), shipped_to, note, aid,
        )
        return {
            "ok": True,
            "status": row["status"],
            "verdict": row["admin_verdict"],
            "decided_at": row["decided_at"].isoformat(),
        }

    @staticmethod
    def _admin_row_to_dict(r: asyncpg.Record) -> dict[str, Any]:
        # carry — collapse with `_row_to_dict` if a third shape appears.
        d = dict(r)
        d["id"] = str(d["id"])
        d["user_id"] = str(d["user_id"])
        if d.get("decided_by"):
            d["decided_by"] = str(d["decided_by"])
        if d.get("admin_scores"):
            d["admin_scores"] = json.loads(d["admin_scores"]) if isinstance(
                d["admin_scores"], str
            ) else d["admin_scores"]
        for k in ("created_at", "decided_at"):
            if d.get(k):
                d[k] = d[k].isoformat()
        d["display_status"] = _derive_display_status(
            d.get("status"), d.get("admin_verdict"), d.get("shipped_to"),
        )
        return d

    @staticmethod
    def _row_to_dict(r: asyncpg.Record) -> dict[str, Any]:
        d = dict(r)
        for k in ("id", "user_id", "decided_by"):
            if d.get(k):
                d[k] = str(d[k])
        for k in ("created_at", "decided_at"):
            if d.get(k):
                d[k] = d[k].isoformat()
        d["display_status"] = _derive_display_status(
            d.get("status"), d.get("admin_verdict"), d.get("shipped_to"),
        )
        return d


class ProposalNotFound(Exception):
    def __init__(self, pid: str) -> None:
        super().__init__(f"proposal not found: {pid}")
        self.pid = pid


class ProposalAlreadyDecided(Exception):
    def __init__(self, pid: str, status: str) -> None:
        super().__init__(f"proposal {pid} already in status {status}")
        self.pid = pid
        self.status = status

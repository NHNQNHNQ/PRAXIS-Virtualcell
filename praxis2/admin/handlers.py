"""8 个 admin v2 ASGI handler:
- 4 个 swap M9 stub (list_users / ledger / audit-log / stats)
- 4 个新加 (adjust / freeze / unfreeze / reconcile)
"""
from __future__ import annotations

import json
import logging
from typing import Any

from praxis2.accounting.ledger import LedgerError
from praxis2.admin.repo import (
    CannotFreezeAdmin,
    UserNotFound,
    clamp_pagination,
)

log = logging.getLogger(__name__)


async def _json(send, status: int, body: dict) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode()
    await send({
        "type": "http.response.start", "status": status,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": payload})


async def _read_body(receive) -> dict:
    chunks = b""
    while True:
        msg = await receive()
        chunks += msg.get("body", b"")
        if not msg.get("more_body"):
            break
    if not chunks:
        return {}
    try:
        return json.loads(chunks)
    except ValueError:
        return {}


def _qs(scope, key: str) -> str | None:
    qs = scope.get("query_string", b"").decode()
    if not qs:
        return None
    from urllib.parse import parse_qs
    return parse_qs(qs).get(key, [None])[0]


def _require_admin(scope) -> tuple[int, dict] | None:
    user = scope.get("user")
    if not user:
        return 401, {"error": "unauthorized", "reason": "未登录"}
    if user.get("role") != "admin":
        return 403, {"error": "forbidden", "reason": "需 admin 权限"}
    return None


# ---------- 4 swap (M9 stub → 真) ----------

async def handle_admin_users_list(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    q = _qs(scope, "q") or ""
    result = await deps["admin_user_repo"].list_users(q=q, page=page, limit=limit)
    await _json(send, 200, result)


async def handle_admin_ledger_list(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    filters: dict[str, Any] = {}
    if (u := _qs(scope, "user_id")):
        filters["user_id"] = u
    if (k := _qs(scope, "kind")):
        filters["kind"] = k
    # ledger inline SQL (没专门 LedgerRepo.query helper; carry)
    args: list[Any] = []
    where: list[str] = []
    import uuid as _uuid
    if filters.get("user_id"):
        args.append(_uuid.UUID(filters["user_id"]))
        where.append(f"user_id=${len(args)}")
    if filters.get("kind"):
        args.append(filters["kind"])
        where.append(f"kind=${len(args)}")
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    args.extend([limit, (page - 1) * limit])
    pg_pool = deps["pg_pool"]
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT id, user_id, amount_li, kind, ref_type, ref_id, "
            f"balance_after, meta, created_at "
            f"FROM ledger{where_sql} "
            f"ORDER BY created_at DESC LIMIT ${len(args)-1} OFFSET ${len(args)}",
            *args,
        )
        total = await conn.fetchval(
            f"SELECT count(*) FROM ledger{where_sql}", *args[:-2],
        )
    out_rows = []
    for r in rows:
        d = dict(r)
        d["user_id"] = str(d["user_id"])
        d["kind_suffix"] = ""  # FE 期望字段;暂空
        if d.get("meta") and isinstance(d["meta"], str):
            d["meta"] = json.loads(d["meta"])
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        out_rows.append(d)
    await _json(send, 200, {
        "rows": out_rows, "total": int(total), "page": page, "limit": limit,
    })


async def handle_admin_audit_list(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    filters: dict[str, Any] = {}
    if (u := _qs(scope, "user_id")):
        filters["user_id"] = u
    if (a := _qs(scope, "action")):
        filters["action"] = a
    result = await deps["audit_repo"].query(filters, page=page, limit=limit)
    await _json(send, 200, result)


async def handle_admin_stats(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    stats = await deps["admin_user_repo"].get_stats()
    await _json(send, 200, stats)


# ---------- 4 new ----------

async def handle_admin_user_adjust(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    admin = scope.get("user")
    target_id = scope.get("path_params", {}).get("user_id", "")
    if not target_id:
        await _json(send, 400, {"error": "missing_user_id"})
        return
    body = await _read_body(receive)
    try:
        amount_yuan = float(body.get("amount_yuan", 0))
    except (ValueError, TypeError):
        await _json(send, 400, {"error": "bad_amount_yuan"})
        return
    note = (body.get("note") or "").strip()
    if not note:
        await _json(send, 400, {"error": "missing_field", "field": "note"})
        return
    amount_li = round(amount_yuan * 100)
    if amount_li == 0:
        await _json(send, 400, {"error": "zero_amount"})
        return

    try:
        async with deps["pg_pool"].acquire() as conn:
            async with conn.transaction():
                result = await deps["admin_user_repo"].adjust_balance(
                    conn, target_id, admin["user_id"], amount_li, note,
                )
                await deps["audit_repo"].insert(
                    conn, user_id=admin["user_id"], actor="admin",
                    action="balance_adjust", resource="user", resource_id=target_id,
                    ip=None, ua=None,
                    meta={"amount_li": amount_li, "note": note,
                          "new_balance_li": result["new_balance_li"]},
                )
    except LedgerError as e:
        await _json(send, 400, {"error": "negative_balance", "reason": str(e)})
        return
    await _json(send, 200, {"ok": True, **result})


async def handle_admin_user_freeze(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    admin = scope.get("user")
    target_id = scope.get("path_params", {}).get("user_id", "")
    body = await _read_body(receive)
    reason = (body.get("reason") or "").strip() or "no reason"

    try:
        async with deps["pg_pool"].acquire() as conn:
            async with conn.transaction():
                result = await deps["admin_user_repo"].freeze(
                    conn, target_id, admin["user_id"], reason,
                )
                if not result["already"]:
                    await deps["audit_repo"].insert(
                        conn, user_id=admin["user_id"], actor="admin",
                        action="user_freeze", resource="user", resource_id=target_id,
                        ip=None, ua=None, meta={"reason": reason},
                    )
    except UserNotFound:
        await _json(send, 404, {"error": "not_found"})
        return
    except CannotFreezeAdmin:
        await _json(send, 403, {"error": "cannot_freeze_admin"})
        return
    await _json(send, 200, {"ok": True, "status": result["status"]})


async def handle_admin_user_unfreeze(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    admin = scope.get("user")
    target_id = scope.get("path_params", {}).get("user_id", "")

    try:
        async with deps["pg_pool"].acquire() as conn:
            async with conn.transaction():
                result = await deps["admin_user_repo"].unfreeze(
                    conn, target_id, admin["user_id"],
                )
                if not result["already"]:
                    await deps["audit_repo"].insert(
                        conn, user_id=admin["user_id"], actor="admin",
                        action="user_unfreeze", resource="user", resource_id=target_id,
                        ip=None, ua=None, meta={},
                    )
    except UserNotFound:
        await _json(send, 404, {"error": "not_found"})
        return
    await _json(send, 200, {"ok": True, "status": result["status"]})


async def handle_admin_reconcile(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    admin = scope.get("user")
    max_users = deps["reconcile_max_users"]
    result = await deps["admin_user_repo"].reconcile(max_users=max_users)
    # 写一条总 audit
    async with deps["pg_pool"].acquire() as conn:
        async with conn.transaction():
            await deps["audit_repo"].insert(
                conn, user_id=admin["user_id"], actor="admin",
                action="reconcile_run", resource="system", resource_id=None,
                ip=None, ua=None,
                meta={"checked": result["checked"], "mismatches": result["mismatches"]},
            )
    await _json(send, 200, result)

"""4 个 proposals ASGI handler — 3 用户面 + 1 admin 决策。"""
from __future__ import annotations

import json
import logging

from praxis2.admin.repo import clamp_pagination
from praxis2.proposals.repo import (
    _PROPOSAL_KIND,
    _PROPOSAL_VERDICT,
    ProposalAlreadyDecided,
    ProposalNotFound,
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


async def handle_proposal_create(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized"})
        return
    body = await _read_body(receive)
    kind = body.get("kind", "")
    title = (body.get("title") or "").strip()
    body_text = body.get("body")

    if kind not in _PROPOSAL_KIND:
        await _json(send, 422, {"error": "invalid_kind",
                                "allowed": sorted(_PROPOSAL_KIND)})
        return
    if not title:
        await _json(send, 400, {"error": "missing_field", "field": "title"})
        return
    if len(title) > 200:
        await _json(send, 400, {"error": "field_too_long", "field": "title", "max": 200})
        return
    if body_text and len(body_text) > 5000:
        await _json(send, 400, {"error": "field_too_long", "field": "body", "max": 5000})
        return

    repo = deps["proposal_repo"]
    audit_repo = deps["audit_repo"]
    rate_per_day = deps["proposals_per_user_per_day"]

    recent = await repo.count_recent(user["user_id"], hours=24)
    if recent >= rate_per_day:
        await _json(send, 429, {"error": "proposal_rate_limit",
                                "limit": rate_per_day, "window_hours": 24})
        return

    async with deps["pg_pool"].acquire() as conn:
        async with conn.transaction():
            pid = await repo.create(conn, user["user_id"], kind, title, body_text)
            await audit_repo.insert(
                conn, user_id=user["user_id"], actor="user",
                action="proposal_create", resource="proposal", resource_id=pid,
                ip=None, ua=None,
                meta={"kind": kind, "title_first_30": title[:30]},
            )
    await _json(send, 200, {
        "id": pid, "status": "open", "state": "submitted",
    })


async def handle_proposal_list_mine(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized"})
        return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    result = await deps["proposal_repo"].list_mine(
        user["user_id"], page=page, limit=limit,
    )
    # Bug(2026-05-31 FE smoke):envelope key 与 admin handler + FE 对齐为 'proposals'
    # (repo 原生返 'rows';FE ProposalsModal 走 r.proposals,不 wrap 会误显"M12 carry")
    await _json(send, 200, {
        "proposals": result["rows"],
        "total": result["total"],
        "page": result["page"],
        "limit": result["limit"],
    })


async def handle_admin_proposal_list(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    filters = {}
    if (s := _qs(scope, "status")):
        filters["status"] = s
    if (k := _qs(scope, "kind")):
        filters["kind"] = k
    result = await deps["proposal_repo"].list_all(filters, page=page, limit=limit)
    # FE 期望 'proposals' 字段(参考 admin.ts)
    await _json(send, 200, {
        "proposals": result["rows"],
        "total": result["total"],
        "page": result["page"],
        "limit": result["limit"],
    })


async def handle_admin_proposal_decide(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    admin = scope.get("user")
    pid = scope.get("path_params", {}).get("proposal_id", "")
    if not pid:
        await _json(send, 400, {"error": "missing_proposal_id"})
        return
    body = await _read_body(receive)
    verdict = body.get("verdict", "")
    score = body.get("score")
    shipped_to = body.get("shipped_to")
    note = body.get("note")

    if verdict not in _PROPOSAL_VERDICT:
        await _json(send, 422, {"error": "invalid_verdict",
                                "allowed": sorted(_PROPOSAL_VERDICT)})
        return
    if score is not None and not (isinstance(score, int) and 1 <= score <= 5):
        await _json(send, 422, {"error": "invalid_score", "range": "1-5"})
        return
    if note and len(note) > 1000:
        await _json(send, 400, {"error": "field_too_long", "field": "note", "max": 1000})
        return
    if shipped_to and len(shipped_to) > 200:
        await _json(send, 400, {"error": "field_too_long", "field": "shipped_to", "max": 200})
        return

    try:
        async with deps["pg_pool"].acquire() as conn:
            async with conn.transaction():
                result = await deps["proposal_repo"].decide(
                    conn, pid, admin["user_id"], verdict,
                    score=score, shipped_to=shipped_to, note=note,
                )
                await deps["audit_repo"].insert(
                    conn, user_id=admin["user_id"], actor="admin",
                    action="proposal_decide", resource="proposal", resource_id=pid,
                    ip=None, ua=None,
                    meta={"verdict": verdict, "score": score, "shipped_to": shipped_to},
                )
    except ProposalNotFound:
        await _json(send, 404, {"error": "not_found"})
        return
    except ProposalAlreadyDecided as e:
        await _json(send, 409, {"error": "already_decided", "current_status": e.status})
        return
    await _json(send, 200, result)

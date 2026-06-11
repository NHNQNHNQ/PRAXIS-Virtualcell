"""4 个 spawn ASGI handler。

挂在 server/app.py:
- POST /api/spawn                      handle_spawn_post
- GET  /api/spawn/list                 handle_spawn_list
- GET  /api/spawn/get/{task_id}        handle_spawn_get
- POST /api/spawn/cancel/{task_id}     handle_spawn_cancel
"""
from __future__ import annotations

import asyncio
import json
from typing import Any


async def _json(send, status: int, body: dict) -> None:
    data = json.dumps(body, ensure_ascii=False, default=str).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8")]})
    await send({"type": "http.response.body", "body": data})


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


def _require_user(scope) -> tuple[str, Any]:
    user = scope.get("user")
    if not user:
        return ("unauthorized", None)
    return ("ok", user)


async def create_spawn_task(
    user_id: str, prompt: str, model: str, deps: dict[str, Any],
) -> dict[str, Any]:
    """v0.15.0:把 handle_spawn_post 核心逻辑抽出来,chat-stream auto 模式复用。

    返回 {ok: True, task_id, status} 或 {ok: False, error, **detail}。
    调用方按 ok 字段决定 HTTP 状态 / SSE 事件。
    """
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "missing_prompt"}
    if not isinstance(model, str) or not model:
        return {"ok": False, "error": "bad_model"}

    repo = deps["spawn_repo"]
    registry = deps["spawn_registry"]
    ledger = deps["ledger"]

    active = await repo.count_active(user_id)
    if active >= deps["max_concurrent_per_user"]:
        return {"ok": False, "error": "too_many_active",
                "active": active, "limit": deps["max_concurrent_per_user"]}

    async with deps["pg_pool"].acquire() as conn:
        bal = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1", user_id,
        )
    if bal is None or bal <= 0:
        return {"ok": False, "error": "insufficient_balance", "balance": bal}

    async with deps["pg_pool"].acquire() as conn:
        task_id = await repo.create(conn, user_id, prompt, model)

    from praxis2.spawn.worker import run_spawn_task  # noqa: PLC0415
    coro = run_spawn_task(
        task_id=task_id, user_id=user_id, prompt=prompt, model=model,
        client=deps["llm_client_factory"](),
        repo=repo, ledger=ledger, pg_pool=deps["pg_pool"],
        max_tokens=deps["max_tokens"],
        price_in_per_m=deps["price_in_per_m"],
        price_out_per_m=deps["price_out_per_m"],
        partial_flush_chunks=deps["partial_flush_chunks"],
        keep_last_per_user=deps["keep_last_per_user"],
    )
    task = asyncio.create_task(coro)
    registry.register(task_id, task)
    task.add_done_callback(lambda _t: registry.unregister(task_id))

    return {"ok": True, "task_id": task_id, "status": "pending"}


# error_code → HTTP status 映射,chat-stream 不用(它走 SSE),
# 但 handle_spawn_post 需要把核心函数结果翻译成 HTTP code
_ERROR_HTTP_STATUS = {
    "missing_prompt": 400,
    "bad_model": 400,
    "too_many_active": 429,
    "insufficient_balance": 402,
}


async def handle_spawn_post(scope, receive, send, deps) -> None:
    """POST /api/spawn body {prompt, model?} → 创任务 + 启 asyncio 跑 worker。"""
    status, user = _require_user(scope)
    if status != "ok":
        await _json(send, 401, {"error": "unauthorized"})
        return

    body = await _read_body(receive)
    prompt = body.get("prompt") or ""
    model = body.get("model") or deps["default_model"]

    result = await create_spawn_task(user["user_id"], prompt, model, deps)
    if not result["ok"]:
        err_payload = {k: v for k, v in result.items() if k != "ok"}
        await _json(send, _ERROR_HTTP_STATUS.get(result["error"], 500), err_payload)
        return
    await _json(send, 200, {"id": result["task_id"], "status": result["status"]})


def _serialize_task(row: dict[str, Any]) -> dict[str, Any]:
    """v0.15.0:repo 字段(id/prompt/tokens_in/completed_at)→ FE 期望
    (task_id/message/in_tokens/finished_at)。FE SpawnModal/SpawnTask interface
    已落用这些名字 + 老 bug:任务非空时 t.message.slice 崩。
    """
    return {
        "task_id": row.get("id"),
        "user_id": row.get("user_id"),
        "agent": row.get("agent") or "spawn",  # repo 未存,默认 spawn
        "label": row.get("label"),
        "model": row.get("model"),
        "message": row.get("prompt") or "",
        "status": row.get("status"),
        "answer": row.get("answer"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("completed_at"),
        "exit_code": row.get("exit_code"),
        "in_tokens": row.get("tokens_in") or 0,
        "out_tokens": row.get("tokens_out") or 0,
        "cost_li": row.get("cost_li"),
        "error": row.get("error"),
        "created_at": row.get("created_at"),
    }


async def handle_spawn_list(scope, receive, send, deps) -> None:
    """GET /api/spawn/list → 当前用户最近 100 条任务。"""
    status, user = _require_user(scope)
    if status != "ok":
        await _json(send, 401, {"error": "unauthorized"})
        return
    rows = await deps["spawn_repo"].list_recent(user["user_id"], limit=100)
    await _json(send, 200, {"tasks": [_serialize_task(r) for r in rows]})


async def handle_spawn_get(scope, receive, send, deps) -> None:
    """GET /api/spawn/get/{task_id} → 单条任务详情。"""
    status, user = _require_user(scope)
    if status != "ok":
        await _json(send, 401, {"error": "unauthorized"})
        return
    task_id = scope.get("path_params", {}).get("task_id", "")
    if not task_id:
        await _json(send, 400, {"error": "missing_task_id"})
        return
    row = await deps["spawn_repo"].get(task_id)
    if row is None:
        await _json(send, 404, {"error": "not_found"})
        return
    if row["user_id"] != user["user_id"] and user.get("role") != "admin":
        await _json(send, 404, {"error": "not_found"})  # 不泄露存在
        return
    await _json(send, 200, _serialize_task(row))


async def handle_spawn_cancel(scope, receive, send, deps) -> None:
    """POST /api/spawn/cancel/{task_id} → 取消任务。"""
    status, user = _require_user(scope)
    if status != "ok":
        await _json(send, 401, {"error": "unauthorized"})
        return
    task_id = scope.get("path_params", {}).get("task_id", "")
    if not task_id:
        await _json(send, 400, {"error": "missing_task_id"})
        return
    row = await deps["spawn_repo"].get(task_id)
    if row is None or (row["user_id"] != user["user_id"] and user.get("role") != "admin"):
        await _json(send, 404, {"error": "not_found"})
        return
    if row["status"] not in ("pending", "running"):
        await _json(send, 409, {"error": "not_active", "status": row["status"]})
        return
    cancelled = deps["spawn_registry"].cancel(task_id)
    # 即使 registry 没找到(进程跨重启),仍把 DB 标 cancelled
    if not cancelled:
        await deps["spawn_repo"].update_cancelled(task_id)
    await _json(send, 200, {"ok": True})

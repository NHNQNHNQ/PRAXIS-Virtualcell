"""M10.5 hotfix: M11-M12 endpoint stub。

避免 FE 调用 fall through SPA HTML 报 "got HTML"。
返结构化 JSON(空列表 / 503 not_implemented)。
M11/M12 真接时直接替换 stub。
"""

from __future__ import annotations

import json


async def _json(send, status: int, body: dict) -> None:
    data = json.dumps(body, ensure_ascii=False).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8")]})
    await send({"type": "http.response.body", "body": data})


def _require_user(scope):
    user = scope.get("user")
    if not user:
        return ("unauthorized", 401, {"error": "unauthorized", "reason": "未登录"})
    return ("ok", user)


def _require_admin(scope):
    res = _require_user(scope)
    if res[0] == "unauthorized":
        return res
    user = res[1]
    if user.get("role") != "admin":
        return ("forbidden", 403, {"error": "forbidden", "reason": "需 admin 权限"})
    return ("ok", user)


# ── /api/admin/users/{id}/{adjust,freeze,unfreeze} ──────────────

async def handle_admin_user_adjust_stub(scope, receive, send, deps) -> None:
    res = _require_admin(scope)
    if res[0] != "ok":
        await _json(send, res[1], res[2])
        return
    await _json(send, 503, {"error": "admin_not_implemented", "reason": "M12 carry"})


async def handle_admin_user_freeze_stub(scope, receive, send, deps) -> None:
    res = _require_admin(scope)
    if res[0] != "ok":
        await _json(send, res[1], res[2])
        return
    await _json(send, 503, {"error": "admin_not_implemented", "reason": "M12 carry"})


async def handle_admin_user_unfreeze_stub(scope, receive, send, deps) -> None:
    res = _require_admin(scope)
    if res[0] != "ok":
        await _json(send, res[1], res[2])
        return
    await _json(send, 503, {"error": "admin_not_implemented", "reason": "M12 carry"})


# ── Static ROUTES(动态路径在 app.py prefix dispatch)──────────────

ROUTES: dict[tuple[str, str], str] = {}

"""ASGI 认证中间件:解 cookie → Redis 取 session → 注入 scope["user"]。

包在 `praxis2.server.app._App.__call__` 外层:make_app 工厂返回
AuthMiddleware(_App(deps), redis_client=...)。白名单 endpoint 不强求 cookie,
但 middleware 仍解 cookie(若有)以便 handler 内拿到 user(audit 时用)。
"""

from __future__ import annotations

from dataclasses import dataclass

from praxis2.auth.service import parse_cookie
from praxis2.store.redis import auth_session_get


@dataclass(frozen=True)
class SessionUser:
    user_id: str
    email: str
    role: str


class AuthMiddleware:
    """ASGI middleware 解 cookie → Redis 取 session → scope["user"] 注入。

    Phase A.3:pepper 必传(用于 HMAC(pepper, token) 算 Redis key)。
    """

    def __init__(self, app, redis_client, *, pepper: str) -> None:
        self._app = app
        self._redis = redis_client
        self._pepper = pepper

    async def __call__(self, scope, receive, send):
        # 非 HTTP scope(lifespan/websocket 等)直 pass
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        cookie_header = None
        for k, v in scope.get("headers", []):
            if k == b"cookie":
                cookie_header = v.decode("utf-8", errors="ignore")
                break

        user: dict | None = None
        token = parse_cookie(cookie_header)
        if token:
            data = await auth_session_get(self._redis, token, pepper=self._pepper)
            if data and "user_id" in data:
                user = {
                    "user_id": data["user_id"],
                    "email": data.get("email", ""),
                    "role": data.get("role", "user"),
                }

        new_scope = dict(scope)
        new_scope["user"] = user
        await self._app(new_scope, receive, send)

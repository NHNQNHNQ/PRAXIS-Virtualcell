"""Phase A.5 / reviewer M6 C4:/chat/permission 鉴权 + tenant 绑定。

修复前缺陷:
- handler 完全不校验 scope["user"],任何能拿到 request_id 的人都能 resolve
- PendingPermissionRegistry.register() 不绑 user_id,跨 tenant 也能 resolve

修复后契约:
- 无 cookie → 401 unauthorized
- 有 cookie 但 rid 属另一 user → 403 forbidden(future 仍 pending)
- 有 cookie 且 rid 属自己 → 200 ok
- 有 cookie 但 rid 不存在(已过期/未注册) → 404 not_found
"""

import httpx
import pytest

from tests._auth_test_helpers import make_test_app_deps, preseed_session


@pytest.mark.asyncio
async def test_unauthenticated_resolve_returns_401():
    """无 cookie 直接 POST /chat/permission → 401(handler 必须先校验认证)。"""
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    app = make_app(deps)
    # 用真实 app.permission_registry.register 模拟内核已注册过权限请求
    rid = await _register_via_running_loop(app, user_id="u_a")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/chat/permission",
            json={"request_id": rid, "decision": "allow"},
        )
        assert r.status_code == 401
        assert "unauthorized" in r.text
    # future 必须仍 pending(未被未认证调用解析)
    assert app.permission_registry.is_pending(rid) is True
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_cross_tenant_resolve_returns_403():
    """user_a 注册 rid,user_b 携 cookie POST resolve → 403 forbidden,future 仍 pending。"""
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    app = make_app(deps)
    rid = await _register_via_running_loop(app, user_id="u_a")
    # user_b 的 cookie
    cookie_b = await preseed_session(deps, user_id="u_b", email="b@t.com")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/chat/permission",
            json={"request_id": rid, "decision": "allow"},
            headers={"Cookie": cookie_b},
        )
        assert r.status_code == 403
        assert "forbidden" in r.text
    # 关键:user_a 的 future 仍 pending(跨 tenant 没解析掉)
    assert app.permission_registry.is_pending(rid) is True
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_owner_resolve_returns_200():
    """user_a 注册 rid,user_a 携 cookie POST resolve → 200,future resolved 且 cleanup。"""
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    app = make_app(deps)
    rid = await _register_via_running_loop(app, user_id="u_a")
    cookie_a = await preseed_session(deps, user_id="u_a", email="a@t.com")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/chat/permission",
            json={"request_id": rid, "decision": "allow"},
            headers={"Cookie": cookie_a},
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}
    # cancel 后 rid 不再 pending
    assert app.permission_registry.is_pending(rid) is False
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_unknown_rid_returns_404():
    """认证通过但 rid 不存在(已过期/未注册)→ 404 not_found。"""
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    app = make_app(deps)
    cookie = await preseed_session(deps, user_id="u_a")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/chat/permission",
            json={"request_id": "deadbeef" * 4, "decision": "allow"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 404
        assert "not_found" in r.text
    await deps.redis.aclose()


async def _register_via_running_loop(app, *, user_id: str) -> str:
    """register() 要 running loop;test 内已是 async,直接调即可。

    注意:app 是 _AppWithMiddleware,permission_registry 透传到内层 _App。
    """
    return app.permission_registry.register(user_id=user_id)

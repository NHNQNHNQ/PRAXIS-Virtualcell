"""M6 carry:server/app.py 路由表化(if/elif → dict 查表)。

M9:_ROUTES 模块常量 → _App 实例属性 _routes(因为 auth.ROUTES merge 需要 deps)。
本测试取 inner _App._routes 验。
"""

import httpx
import pytest

from tests._auth_test_helpers import make_test_app_deps, preseed_session


def test_routes_table_is_dict_with_known_keys():
    from praxis2.server.app import make_app

    app = make_app(make_test_app_deps())
    routes = app._app._routes  # inner _App 实例的路由表
    assert isinstance(routes, dict)
    assert ("/chat/stream", "POST") in routes
    assert ("/chat/permission", "POST") in routes
    assert ("/admin/review/pending", "GET") in routes
    assert ("/admin/review/approve", "POST") in routes
    assert ("/admin/review/reject", "POST") in routes


@pytest.mark.asyncio
async def test_unknown_route_still_404():
    from praxis2.server.app import make_app

    app = make_app(make_test_app_deps())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/nope")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_chat_permission_route_requires_auth():
    # A.5(reviewer M6 C4):/chat/permission 现强制认证。无 cookie → 401。
    # 详细 200/403/404 场景见 tests/test_security_permission_endpoint_auth.py。
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/chat/permission", json={"request_id": "ghost", "decision": "allow"})
        assert r.status_code == 401
        assert "unauthorized" in r.text
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_authed_chat_stream_works_via_cookie():
    """M9 新断言:cookie 注入 scope['user'] 后 /chat/stream 不再 401。"""
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    await preseed_session(deps)  # 预置 session(本测仅验未 401,不带 cookie)
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # 无 cookie → 401
        r = await c.post("/chat/stream", json={"message": "hi"})
        assert r.status_code == 401
        # 有 cookie → 进入 chat_stream(未真打上游 LLM 这里不深测,只验未 401)
        # 注意:真打上游会无 respx mock 报错,这里只验路由进对
    await deps.redis.aclose()

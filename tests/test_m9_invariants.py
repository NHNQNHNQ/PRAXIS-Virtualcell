"""M9 横向不变量(整合 §0.1 不干扰 v1 + §11.6 多租户 + cookie 失效)。

每条不变量都是测试,确保 M9 ship 时这些约束都仍硬约束(不被某 task 实现误破)。
"""

from __future__ import annotations

import httpx
import pytest


async def _register(client: httpx.AsyncClient, email: str, pw: str = "pw12345"):
    r = await client.post(
        "/api/auth/email/send-code", json={"email": email, "purpose": "register"}
    )
    code = r.json()["dev_code"]
    r = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "code": code,
            "password": pw,
            "display_name": email,
        },
    )
    token = r.headers["set-cookie"].split("praxis_session=")[1].split(";")[0]
    return token, r.json()["user"]["id"]  # handle_register still nests user


@pytest.mark.asyncio
async def test_inv1_multi_tenant_user_a_cannot_query_b_via_cookie():
    """§11.6 不变量:用户 A 的 cookie 不能拉 B 的 /api/me。"""
    from praxis2.server.app import make_app
    from tests._auth_test_helpers import make_test_app_deps

    deps = make_test_app_deps()
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        tok_a, _ = await _register(c, "a@inv.com")
        await deps.redis.delete("email_throttle:b@inv.com")
        tok_b, _ = await _register(c, "b@inv.com")

        # A 用自己 cookie 拉 me 得 A
        r = await c.get("/api/me", headers={"Cookie": f"praxis_session={tok_a}"})
        assert r.status_code == 200 and r.json()["email"] == "a@inv.com"

        # B 用自己 cookie 拉 me 得 B
        r = await c.get("/api/me", headers={"Cookie": f"praxis_session={tok_b}"})
        assert r.status_code == 200 and r.json()["email"] == "b@inv.com"
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_inv2_chat_stream_401_when_cookie_expired():
    """§11.6 不变量:cookie 失效后 chat-stream 立即 401(不开 SSE 流)。"""
    from praxis2.server.app import make_app
    from praxis2.store.redis import auth_session_del
    from tests._auth_test_helpers import make_test_app_deps

    deps = make_test_app_deps()
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        tok, _ = await _register(c, "a@inv.com")
        # 主动清 session 模拟失效
        await auth_session_del(deps.redis, tok, pepper=deps.settings.password_pepper)

        r = await c.post(
            "/api/chat-stream",
            headers={"Cookie": f"praxis_session={tok}"},
            json={"message": "hi", "session_id": "s1"},
        )
        assert r.status_code == 401
        assert r.headers["content-type"].startswith("application/json")
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_inv3_soft_delete_then_reregister_same_email_works():
    """design §2.4 不变量:partial unique WHERE deleted_at IS NULL 允许重注。"""
    from praxis2.server.app import make_app
    from tests._auth_test_helpers import make_test_app_deps

    deps = make_test_app_deps()
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        tok, _ = await _register(c, "del@inv.com")
        r = await c.request(
            "DELETE",
            "/api/me/account",
            headers={"Cookie": f"praxis_session={tok}"},
        )
        assert r.status_code == 200
        await deps.redis.delete("email_throttle:del@inv.com")
        tok2, _ = await _register(c, "del@inv.com")
        assert tok2 != tok
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_inv4_logout_all_kills_all_sessions():
    """logout-all 不变量:同用户多次登录后 logout-all 杀全部 session。"""
    from praxis2.server.app import make_app
    from tests._auth_test_helpers import make_test_app_deps

    deps = make_test_app_deps()
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        tok1, _ = await _register(c, "la@inv.com")
        # 模拟另一设备登录
        r = await c.post(
            "/api/auth/login",
            json={"email": "la@inv.com", "password": "pw12345"},
        )
        tok2 = r.headers["set-cookie"].split("praxis_session=")[1].split(";")[0]
        assert tok2 != tok1

        # logout-all 用 tok1
        r = await c.post(
            "/api/auth/logout-all",
            headers={"Cookie": f"praxis_session={tok1}"},
        )
        assert r.status_code == 200
        assert r.json()["sessions_killed"] >= 2

        # tok2 也不可用
        r = await c.get("/api/me", headers={"Cookie": f"praxis_session={tok2}"})
        assert r.status_code == 401
    await deps.redis.aclose()


def test_inv5_v1_backend_still_healthy():
    """§0.1 不变量:M9 全程不干扰 v1 — .53:7788 健康。

    本测试在无网络/无 v1 时自动 skip;装上线时必检。
    """
    import socket
    import urllib.request

    try:
        sock = socket.create_connection(("10.102.106.53", 7788), timeout=2)
        sock.close()
    except (TimeoutError, OSError):
        pytest.skip("v1 后端 .53:7788 不可达(无网络或 v1 未运行)— 跳过 inv5")
    with urllib.request.urlopen(
        "http://10.102.106.53:7788/api/info", timeout=3
    ) as r:
        assert r.status == 200
        body = r.read()
        assert b"PRAXIS-hou" in body  # v1 服务名


def test_inv6_routes_table_has_all_m9_endpoints():
    """M9 _routes 必含 9 + 6 = 15 endpoint(M9 新加 9 + M0-M8 老 6)。"""
    from praxis2.server.app import make_app
    from tests._auth_test_helpers import make_test_app_deps

    deps = make_test_app_deps()
    app = make_app(deps)
    routes = app._app._routes
    # M9 新增
    for path, method in [
        ("/api/auth/email/send-code", "POST"),
        ("/api/auth/register", "POST"),
        ("/api/auth/login", "POST"),
        ("/api/auth/logout", "POST"),
        ("/api/auth/logout-all", "POST"),
        ("/api/me", "GET"),
        ("/api/me/balance", "GET"),
        ("/api/me/account", "DELETE"),
        ("/api/info", "GET"),
        ("/api/chat-stream", "POST"),
    ]:
        assert (path, method) in routes, f"missing {method} {path}"
    # M0-M8 沿用
    for path, method in [
        ("/chat/stream", "POST"),
        ("/chat/permission", "POST"),
        ("/admin/review/pending", "GET"),
        ("/admin/review/approve", "POST"),
        ("/admin/review/reject", "POST"),
    ]:
        assert (path, method) in routes, f"missing {method} {path}"

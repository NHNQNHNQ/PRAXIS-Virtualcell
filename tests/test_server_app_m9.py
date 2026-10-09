"""server.app M9 改造测试:_ROUTES merge / chat-stream alias / 400→401 / lifespan。"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest


def _make_deps_for_test():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.auth.email import DevEmailGateway
    from praxis2.auth.repository import FakeAuthRepository
    from praxis2.server.app import AppDeps
    from praxis2.store.memory import InMemoryStore

    @dataclass
    class _S:
        anthropic_api_key: str = "sk-x"
        anthropic_base_url: str = "https://api.anthropic.com"
        model: str = "claude-3-5-sonnet-20241022"
        max_tokens: int = 4096
        max_turns: int = 30
        recovery_budget: int = 3
        max_output_recovery: int = 2
        host: str = "0.0.0.0"
        port: int = 8001
        workers: int = 1
        max_concurrent_per_user: int = 2
        user_qps: float = 10.0
        global_llm_inflight: int = 100
        quota_global_max_queued: int = 200
        dump_prompts: str = ""
        max_heavy_jobs_per_user: int = 0
        db_url: str = ""
        redis_url: str = ""
        password_pepper: str = "test-pepper"
        cookie_secure: bool = False
        cookie_samesite: str = "Lax"
        session_ttl_days: int = 30
        allow_self_signup: bool = True
        smtp_host: str = ""
        smtp_port: int = 0
        smtp_user: str = ""
        smtp_password: str = ""
        smtp_from: str = ""
        signup_gift_li: int = 10000
        env_label: str = "dev"
        permission_ask_timeout_s: float = 60.0
        allowed_origins: str = ""
        static_root: str = ""
        files_root: str = "/tmp/praxis2-test-files"
        files_quota_bytes: int = 100 * 1024**3
        files_max_per_file_bytes: int = 20 * 1024**3
        # M11.1 spawn
        spawn_max_concurrent_per_user: int = 2
        spawn_keep_last_per_user: int = 100
        spawn_partial_flush_chunks: int = 20
        llm_price_in_per_m_li: int = 1500
        llm_price_out_per_m_li: int = 6000
        # M11.2 MD + HPC SSH
        hpc_ssh_host: str = "10.102.106.53"
        hpc_ssh_user: str = "zkyd"
        hpc_ssh_key_path: str = "/tmp/fake-key"
        hpc_ssh_timeout_s: float = 15.0
        md_hpc_account: str = "SCW6CHB"
        md_price_gpu_per_h_li: int = 10000
        md_price_cpu_per_h_li: int = 500
        md_free_cpu_hours_per_job: float = 1.0
        md_max_concurrent_per_user: int = 2
        md_poll_interval_s: int = 30
        md_check_gpus_script_path: str = "~/check_gpus.sh"
        md_gromacs_load_cmd: str = "conda activate praxis-md-cuda"
        # M12 admin v2 + proposals
        admin_reconcile_max_users: int = 1000
        proposals_per_user_per_day: int = 20

    return AppDeps(
        settings=_S(),
        store=InMemoryStore(),
        api_key="sk-x",
        base_url="https://api.anthropic.com",
        repo=FakeAuthRepository(),
        redis=fakeredis.aioredis.FakeRedis(decode_responses=True),
        email_gateway=DevEmailGateway(),
    )


def test_routes_table_includes_auth_endpoints():
    from praxis2.server.app import make_app

    deps = _make_deps_for_test()
    app = make_app(deps)
    inner = app._app
    assert ("/api/auth/email/send-code", "POST") in inner._routes
    assert ("/api/auth/register", "POST") in inner._routes
    assert ("/api/me", "GET") in inner._routes
    assert ("/api/info", "GET") in inner._routes


def test_chat_stream_alias_registered():
    from praxis2.server.app import make_app

    app = make_app(_make_deps_for_test())
    inner = app._app
    assert ("/api/chat-stream", "POST") in inner._routes
    assert ("/chat/stream", "POST") in inner._routes


@pytest.mark.asyncio
async def test_chat_stream_returns_401_when_no_cookie():
    from praxis2.server.app import make_app

    app = make_app(_make_deps_for_test())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.post("/api/chat-stream", json={"message": "hi", "session_id": "s1"})
        assert r.status_code == 401
        # fixup I1:401 schema 统一为 {"error": "unauthorized", "reason": "..."}
        body = r.json()
        assert body["error"] == "unauthorized"
        assert "未登录" in body["reason"]


@pytest.mark.asyncio
async def test_old_chat_stream_path_also_returns_401_when_no_cookie():
    from praxis2.server.app import make_app

    app = make_app(_make_deps_for_test())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.post("/chat/stream", json={"message": "hi", "session_id": "s1"})
        assert r.status_code == 401  # M9:400 → 401


@pytest.mark.asyncio
async def test_info_endpoint_white_listed_no_cookie_returns_200():
    from praxis2.server.app import make_app

    app = make_app(_make_deps_for_test())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.get("/api/info")
        assert r.status_code == 200
        d = r.json()
        assert d["service"] == "PRAXIS-2"
        assert d["env"] == "dev"


@pytest.mark.asyncio
async def test_404_on_unknown_path():
    from praxis2.server.app import make_app

    app = make_app(_make_deps_for_test())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.get("/nope")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_register_login_full_flow_via_app():
    from praxis2.server.app import make_app

    app = make_app(_make_deps_for_test())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.post(
            "/api/auth/email/send-code",
            json={"email": "a@b.com", "purpose": "register"},
        )
        assert r.status_code == 200
        code = r.json()["dev_code"]
        r = await client.post(
            "/api/auth/register",
            json={
                "email": "a@b.com",
                "code": code,
                "password": "pw12345",
                "display_name": "A",
            },
        )
        assert r.status_code == 200
        set_cookie = r.headers.get("set-cookie")
        assert set_cookie and "praxis_session=" in set_cookie
        token = set_cookie.split("praxis_session=")[1].split(";")[0]
        r = await client.get("/api/me", headers={"Cookie": f"praxis_session={token}"})
        assert r.status_code == 200
        assert r.json()["email"] == "a@b.com"


def test_permission_bridge_uses_get_running_loop():
    """M8 carry:register() 不应用 asyncio.get_event_loop()。"""
    import inspect

    from praxis2.server.permission_bridge import PendingPermissionRegistry

    src = inspect.getsource(PendingPermissionRegistry.register)
    assert "get_event_loop" not in src
    assert "get_running_loop" in src


# fixup-2(reviewer I1-residual):auth/routes.py 内 4 处 401 的 schema 必须统一为
# {"error": "unauthorized", "reason": "..."},不能残留旧 shape {"error": "未登录"}。
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/api/me"),
        ("GET", "/api/me/balance"),
        ("DELETE", "/api/me/account"),
        ("POST", "/api/auth/logout-all"),
    ],
)
async def test_auth_me_401_schema_unified(method, path):
    """无 cookie 命中这 4 个 handler 时,401 body 必须含 error=unauthorized + reason。"""
    from praxis2.server.app import make_app

    app = make_app(_make_deps_for_test())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.request(method, path)
        assert r.status_code == 401, (
            f"{method} {path}:期望 401,实际 {r.status_code}"
        )
        body = r.json()
        assert body.get("error") == "unauthorized", (
            f"{method} {path}:旧 shape 残留,body={body!r}"
        )
        assert "reason" in body, f"{method} {path}:缺 reason 字段,body={body!r}"
        assert "未登录" in body["reason"], (
            f"{method} {path}:reason 不含『未登录』,body={body!r}"
        )

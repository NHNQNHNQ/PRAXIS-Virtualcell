"""M11.1 集成测试 — 5 路径覆盖。

依赖 tests/integration/conftest.py 的 app_with_real_backends fixture
(启 PG+Redis containers + alembic + ASGI app)。
"""
import asyncio
import uuid

import httpx
import pytest

from tests._llm_fakes import FakeLLMClient, RaisingLLMClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


async def _register_user(client: httpx.AsyncClient, email: str) -> str:
    """走 register flow,返回 praxis_session cookie token。"""
    r = await client.post(
        "/api/auth/email/send-code",
        json={"email": email, "purpose": "register"},
    )
    assert r.status_code == 200, r.text
    code = r.json()["dev_code"]
    r = await client.post(
        "/api/auth/register",
        json={
            "email": email, "code": code,
            "password": "spawn-test-pw", "display_name": "spawn-test",
        },
    )
    assert r.status_code == 200, r.text
    sc = r.headers["set-cookie"]
    return sc.split("praxis_session=")[1].split(";")[0]


async def _set_balance(pool, email: str, balance_li: int) -> str:
    """直接 SQL 写 user.balance_li(register 后默认 0/signup_gift,这里覆盖)。
    返 user_id。"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE users SET balance_li=$1 WHERE email=$2 RETURNING id",
            balance_li, email,
        )
    return str(row["id"])


def _auth_headers(token: str) -> dict[str, str]:
    return {"Cookie": f"praxis_session={token}"}


async def test_happy_path(app_with_real_backends):
    """POST /api/spawn → 200 → poll get → done。"""
    app, pool, _ = app_with_real_backends
    fake = FakeLLMClient(turns=[[
        {"type": "text", "text": "hello"},
        {"type": "message_stop", "stop_reason": "end_turn",
         "usage": {"input_tokens": 100, "output_tokens": 50}},
    ]])
    app._app._spawn_deps["llm_client_factory"] = lambda: fake

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        email = f"happy-{uuid.uuid4()}@x.x"
        token = await _register_user(client, email)
        await _set_balance(pool, email, 100000)

        resp = await client.post(
            "/api/spawn", json={"prompt": "你好"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        task_id = resp.json()["id"]

        # poll 至 done(5s 超时)
        row = None
        for _ in range(50):
            await asyncio.sleep(0.1)
            r = await client.get(
                f"/api/spawn/get/{task_id}", headers=_auth_headers(token),
            )
            row = r.json()
            if row.get("status") == "done":
                break
        else:
            pytest.fail(f"task didn't reach done, last={row}")

        assert row["answer"] == "hello"
        assert row["tokens_in"] == 100
        assert row["tokens_out"] == 50
        # ceil((100*1500+50*6000)/1e6) = ceil(0.45) = 1
        assert row["cost_li"] == 1


async def test_cancel_running(app_with_real_backends):
    """POST → cancel before message_stop → status=cancelled,no debit。"""
    app, pool, _ = app_with_real_backends
    blocking = asyncio.Event()

    class SlowClient:
        async def stream_messages(self, **kw):
            yield {"type": "text", "text": "partial"}
            try:
                await blocking.wait()
            finally:
                pass
            yield {"type": "message_stop", "stop_reason": "end_turn",
                   "usage": {"input_tokens": 0, "output_tokens": 0}}

        async def aclose(self): pass

    app._app._spawn_deps["llm_client_factory"] = lambda: SlowClient()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        email = f"cancel-{uuid.uuid4()}@x.x"
        token = await _register_user(client, email)
        await _set_balance(pool, email, 100000)

        r = await client.post(
            "/api/spawn", json={"prompt": "p"}, headers=_auth_headers(token),
        )
        tid = r.json()["id"]
        await asyncio.sleep(0.1)   # 让 worker 跑起来 + 至少处理一个 chunk

        rc = await client.post(
            f"/api/spawn/cancel/{tid}", headers=_auth_headers(token),
        )
        assert rc.status_code == 200

        row = None
        for _ in range(40):
            await asyncio.sleep(0.05)
            r = await client.get(
                f"/api/spawn/get/{tid}", headers=_auth_headers(token),
            )
            row = r.json()
            if row.get("status") == "cancelled":
                break
        assert row["status"] == "cancelled"
        assert row["cost_li"] == 0


async def test_quota_insufficient_balance(app_with_real_backends):
    """user.balance_li <= 0 → 402 insufficient_balance,不创 task。"""
    app, pool, _ = app_with_real_backends
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        email = f"noquota-{uuid.uuid4()}@x.x"
        token = await _register_user(client, email)
        await _set_balance(pool, email, 0)

        r = await client.post(
            "/api/spawn", json={"prompt": "p"}, headers=_auth_headers(token),
        )
        assert r.status_code == 402
        assert r.json()["error"] == "insufficient_balance"


async def test_concurrent_over_limit(app_with_real_backends):
    """已 2 个 active → 第 3 个 → 429 too_many_active。"""
    app, pool, _ = app_with_real_backends
    blocking = asyncio.Event()

    class BlockClient:
        async def stream_messages(self, **kw):
            yield {"type": "text", "text": "."}
            await blocking.wait()
            yield {"type": "message_stop", "stop_reason": "end_turn",
                   "usage": {"input_tokens": 0, "output_tokens": 0}}

        async def aclose(self): pass

    app._app._spawn_deps["llm_client_factory"] = lambda: BlockClient()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        email = f"concur-{uuid.uuid4()}@x.x"
        token = await _register_user(client, email)
        await _set_balance(pool, email, 100000)

        r1 = await client.post(
            "/api/spawn", json={"prompt": "p1"}, headers=_auth_headers(token),
        )
        r2 = await client.post(
            "/api/spawn", json={"prompt": "p2"}, headers=_auth_headers(token),
        )
        assert r1.status_code == 200 and r2.status_code == 200
        await asyncio.sleep(0.1)

        r3 = await client.post(
            "/api/spawn", json={"prompt": "p3"}, headers=_auth_headers(token),
        )
        assert r3.status_code == 429
        assert r3.json()["error"] == "too_many_active"

        blocking.set()   # 清理


async def test_llm_error_marks_failed(app_with_real_backends):
    """LLM 抛 → status=failed + error 存。"""
    app, pool, _ = app_with_real_backends
    app._app._spawn_deps["llm_client_factory"] = (
        lambda: RaisingLLMClient(RuntimeError("upstream 500"))
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        email = f"err-{uuid.uuid4()}@x.x"
        token = await _register_user(client, email)
        await _set_balance(pool, email, 100000)

        r = await client.post(
            "/api/spawn", json={"prompt": "p"}, headers=_auth_headers(token),
        )
        tid = r.json()["id"]

        row = None
        for _ in range(40):
            await asyncio.sleep(0.05)
            r = await client.get(
                f"/api/spawn/get/{tid}", headers=_auth_headers(token),
            )
            row = r.json()
            if row.get("status") == "failed":
                break
        assert row["status"] == "failed"
        assert "upstream 500" in row["error"]

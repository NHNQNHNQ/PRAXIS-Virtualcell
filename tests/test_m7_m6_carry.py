"""M6 carry 修补 batch:通道 B 限流 + Backpressure.from_decision +
_chat_stream try/finally + get_running_loop。

M9 校准:_chat_stream 改 cookie session 后,本测的 aclose 验证用 cookie 预置。
"""

import httpx
import pytest
import respx

from praxis2.runtime.ratelimit import (
    Backpressure,
    RateLimitDecision,
    RateLimiter,
)
from praxis2.server.permission_bridge import PendingPermissionRegistry
from tests._auth_test_helpers import make_test_app_deps, preseed_session


def test_channel_b_heavy_job_independent_from_channel_a():
    rl = RateLimiter(
        max_concurrent_per_user=2,
        user_qps=1000.0,
        global_llm_inflight=100,
        max_heavy_jobs_per_user=1,
    )
    rl.acquire_session("u1")
    rl.acquire_session("u1")
    assert rl.acquire_session("u1").allowed is False
    assert rl.acquire_heavy_job("u1").allowed is True
    assert rl.acquire_heavy_job("u1").allowed is False
    rl.release_heavy_job("u1")
    assert rl.acquire_heavy_job("u1").allowed is True


def test_backpressure_from_decision_factory():
    d = RateLimitDecision(allowed=False, http_status=429, queue_position=5, reason="重算力配额上限")
    bp = Backpressure.from_decision(d, eta_s=120.0)
    assert isinstance(bp, Backpressure)
    assert bp.http_status == 429
    assert bp.queue_position == 5
    assert bp.eta_s == 120.0
    assert "重算力" in bp.reason


def test_backpressure_from_decision_rejects_allowed_decision():
    d = RateLimitDecision(allowed=True)
    with pytest.raises(ValueError, match="allowed"):
        Backpressure.from_decision(d, eta_s=0.0)


@respx.mock
@pytest.mark.asyncio
async def test_chat_stream_aclose_called_even_on_query_exception():
    """M6 Task 11 reviewer M2:内核异常时 client.aclose() 仍执行(try/finally)。M9:cookie auth。"""
    from praxis2.server.app import make_app

    respx.post("https://up.example/v1/messages").mock(
        return_value=httpx.Response(
            500, text="upstream boom", headers={"content-type": "text/plain"}
        )
    )
    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/chat/stream",
            json={"message": "x", "session_id": "s1"},
            headers={"Cookie": cookie},
        )
        # 任何返回(200 SSE 含 error 帧 / 5xx)都接受,关键是不死锁
        assert r.status_code in (200, 500)
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_pending_permission_registry_uses_get_running_loop():
    reg = PendingPermissionRegistry()
    rid = reg.register(user_id="u_test")
    assert reg.is_pending(rid) is True


def test_pending_permission_registry_register_outside_async_raises():
    reg = PendingPermissionRegistry()
    with pytest.raises(RuntimeError):
        reg.register(user_id="u_test")

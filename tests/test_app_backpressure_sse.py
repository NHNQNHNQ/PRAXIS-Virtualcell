"""M7 carry:Backpressure.from_decision 接入 /chat/stream SSE 出口。

M9 校准:user_id 来源 cookie,占满限流前需先预置 session。
"""

import httpx
import pytest

from tests._auth_test_helpers import make_test_app_deps, preseed_session


@pytest.mark.asyncio
async def test_backpressure_sse_event_emitted_on_overload():
    """构造 u1 占满 RateLimiter 后,下次请求经 from_decision → SSE error 帧。"""
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    rl = app.rate_limiter
    # 占满 max_concurrent_per_user=2(_App.__init__ 默认低值方便测)
    assert rl.acquire_session("u1").allowed is True
    while rl.acquire_session("u1").allowed:
        pass

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/chat/stream",
            json={"message": "x", "session_id": "s1"},
            headers={"Cookie": cookie},
        )
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.text
        assert "event: error" in body
        assert "queue_position" in body
    await deps.redis.aclose()

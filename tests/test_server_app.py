"""§3 chat/stream + chat/permission ASGI 路由(M9:user_id 来源切 cookie session)。"""

import httpx
import pytest
import respx

from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests._llm_fakes import TURN_FINAL_TEXT, FakeLLMClient


@pytest.mark.asyncio
async def test_chat_stream_returns_sse_content_type_and_event_set(monkeypatch):
    # §5⑥ 契约:/chat/stream 返回 text/event-stream + 完整消息集形状(M9:cookie auth)
    import praxis2.server.app as _app_mod

    monkeypatch.setattr(
        _app_mod, "AnthropicClient",
        lambda **kwargs: FakeLLMClient(turns=[TURN_FINAL_TEXT]),
    )
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/chat/stream",
            json={"message": "你好", "session_id": "s1"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.text
        assert "event: text_delta" in body
        assert "event: final" in body
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_chat_stream_rejects_no_cookie_401():
    # §11.6 校准(M9):无 cookie session → 401(原 M6 是 400 body 缺 user_id)
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/chat/stream", json={"message": "hi"})
        assert r.status_code == 401
        assert "未登录" in r.text
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_chat_permission_post_resolves_pending():
    # A.5(reviewer M6 C4):resolve 现要求认证 + owner 匹配。
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    app = make_app(deps)
    deps_reg = app.permission_registry
    rid = deps_reg.register(user_id="u1")
    cookie = await preseed_session(deps, user_id="u1")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/chat/permission",
            json={"request_id": rid, "decision": "allow"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200
    assert deps_reg.is_pending(rid) is False
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_unknown_route_404():
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/nope")
        assert r.status_code == 404
    await deps.redis.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_concurrent_same_session_serialized_no_transcript_corruption(monkeypatch):
    import asyncio

    import praxis2.server.app as _app_mod

    monkeypatch.setattr(
        _app_mod, "AnthropicClient",
        lambda **kwargs: FakeLLMClient(turns=[TURN_FINAL_TEXT] * 10),
    )
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:

        async def hit() -> int:
            r = await c.post(
                "/chat/stream",
                json={"message": "x", "session_id": "s1"},
                headers={"Cookie": cookie},
            )
            return r.status_code

        codes = await asyncio.gather(hit(), hit())
        assert codes == [200, 200]
    await deps.redis.aclose()

"""TEST-AGENT-FRAMEWORK §5 端到端:chat-stream 接 resolve_agent 后,
不同 body.agent 走不同 mode-aware 注册 + 非法 spec 不崩。

不依赖真 LLM —— FakeLLMClient 模拟 text-only 流,验证:
1. body.agent="cell" → 200 + SSE 流(discipline,无 AgentTool)
2. body.agent="general" → 200 + SSE 流(含 AgentTool)
3. body.agent=非法 → 200 + SSE 流 + agent_route_warning stream_event
4. 缺 body.agent → 默认 general,200 + SSE 流
"""

import httpx
import pytest

from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests._llm_fakes import TURN_FINAL_TEXT, FakeLLMClient


@pytest.mark.asyncio
async def test_chat_stream_with_discipline_agent_returns_sse(monkeypatch) -> None:
    """body.agent='cell' (discipline) → 200 + 正常 SSE 流。"""
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
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post(
            "/api/chat-stream",
            json={"message": "基因扰动帮我看", "agent": "virtualcell", "session_id": "s1"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.text
        assert "event: text_delta" in body
        assert "event: final" in body
        # 学科 agent 流里不该出现 agent_route_warning(合法 spec)
        assert "agent_route_warning" not in body
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_chat_stream_with_general_agent_returns_sse(monkeypatch) -> None:
    """body.agent='general' → 200 + 正常 SSE 流。"""
    import praxis2.server.app as _app_mod

    monkeypatch.setattr(
        _app_mod, "AnthropicClient",
        lambda **kwargs: FakeLLMClient(turns=[TURN_FINAL_TEXT]),
    )
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u2")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post(
            "/api/chat-stream",
            json={"message": "你好", "agent": "general", "session_id": "s1"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200
        assert "event: final" in r.text
        assert "agent_route_warning" not in r.text
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_chat_stream_with_illegal_agent_falls_back_and_emits_warning(monkeypatch) -> None:
    """非法 spec → fallback general,但不崩;流里出现 agent_route_warning。"""
    import praxis2.server.app as _app_mod

    monkeypatch.setattr(
        _app_mod, "AnthropicClient",
        lambda **kwargs: FakeLLMClient(turns=[TURN_FINAL_TEXT]),
    )
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u3")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post(
            "/api/chat-stream",
            json={
                "message": "hi",
                "agent": "not-a-real-agent-xyz",
                "session_id": "s1",
            },
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200
        body = r.text
        # fallback general 后仍能正常出流
        assert "event: final" in body
        # 警告事件作为 stream_event 发出(前端按 original.type 容错)
        assert "agent_route_warning" in body
        assert "fallback_to" in body
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_chat_stream_without_agent_defaults_to_general(monkeypatch) -> None:
    """body 缺 agent 字段 → 默认 general,不发警告。"""
    import praxis2.server.app as _app_mod

    monkeypatch.setattr(
        _app_mod, "AnthropicClient",
        lambda **kwargs: FakeLLMClient(turns=[TURN_FINAL_TEXT]),
    )
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u4")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post(
            "/api/chat-stream",
            json={"message": "hi", "session_id": "s1"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200
        assert "event: final" in r.text
        assert "agent_route_warning" not in r.text
    await deps.redis.aclose()

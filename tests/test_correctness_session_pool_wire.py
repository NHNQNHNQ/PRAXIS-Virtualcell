"""D.1(reviewer M6 #9):SessionPool 接进 _chat_stream,多轮 phase/messages 不丢。

修复前:_chat_stream 每请求新建 State(),messages 只来自单次入参 → 服务端跨轮
状态(phase、recovery_attempts、stop_hook_reasons、tool_use_context)每次重置。
修复后:同 (user_id, session_id) 走 SessionPool.get/put 复用 State 实例;
不同 session 或不同 user 严格隔离(§11.6 多租户)。
"""

from __future__ import annotations

import asyncio
import json as _json

import pytest

from tests._auth_test_helpers import make_test_app_deps, preseed_session


async def _drive_chat_stream(
    app, cookie: str, *, message: str, session_id: str = "s1"
):
    """直接走 ASGI,收集 body frames。返回 [bytes, ...]。"""
    arrivals: list[bytes] = []
    started = {"v": False}

    async def receive():
        return {
            "type": "http.request",
            "body": _json.dumps({"message": message, "session_id": session_id}).encode(),
            "more_body": False,
        }

    async def send(msg):
        if msg["type"] == "http.response.start":
            started["v"] = True
        elif msg["type"] == "http.response.body":
            body = msg.get("body", b"")
            if body:
                arrivals.append(body)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat/stream",
        "headers": [(b"cookie", cookie.encode())],
        "query_string": b"",
    }
    await app(scope, receive, send)
    assert started["v"], "http.response.start 未发送"
    return arrivals


def _install_inspect_query(monkeypatch, captured: list):
    """安装 fake query:每次调用 append 一份 state 快照(messages 浅拷),
    并在 state 上写一个 phase 标记验证跨请求持久化。"""
    from praxis2.server import app as app_module

    async def fake_query(state, *, client, registry, settings, runner, compactor, **_kw):
        # 快照:此请求开始时(_chat_stream 已 append user msg)的 state
        captured.append(
            {
                "messages": list(state.messages),  # 浅拷,够断言
                "phase": getattr(state, "_test_phase", None),
                "turn_count": state.turn_count,
            }
        )
        # 在 state 上推进 phase + 模拟一轮:这次写一个标记,下一次请求应仍能读到
        state._test_phase = "RETRIEVE"
        state.turn_count += 1
        # 模型回 assistant 一句,加进 messages(query 内核真实路径也会 append)
        state.messages.append({"role": "assistant", "content": "ok"})
        yield {"type": "text", "text": "ok"}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)


@pytest.mark.asyncio
async def test_same_session_preserves_state_across_requests(monkeypatch):
    """连续两次 /chat/stream 同 user+session,服务端 State 复用:
    - 第二次请求开始时 state.messages 应含第一次的 user+assistant,再追加第二次 user
    - state._test_phase 仍是 "RETRIEVE"(第一次写入,第二次没被 State() 重置)
    - state.turn_count 持久(不归零)
    """
    from praxis2.server.app import make_app

    captured: list[dict] = []
    _install_inspect_query(monkeypatch, captured)

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)

    await _drive_chat_stream(app, cookie, message="hello", session_id="s1")
    await _drive_chat_stream(app, cookie, message="follow-up", session_id="s1")
    await deps.redis.aclose()

    assert len(captured) == 2, f"应捕获 2 次 query 调用,实际 {len(captured)}"

    # 第一次:仅 1 条 user 消息;phase=None;turn_count=0
    first = captured[0]
    assert first["messages"] == [{"role": "user", "content": "hello"}]
    assert first["phase"] is None
    assert first["turn_count"] == 0

    # 第二次:state 应被复用 — messages 累积(user hello / assistant ok / user follow-up),
    # phase 仍 RETRIEVE(GAP-B-1 相位恢复)。
    second = captured[1]
    assert second["messages"] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "follow-up"},
    ], f"messages 未累积:{second['messages']!r}"
    assert second["phase"] == "RETRIEVE", (
        f"phase 应仍为 RETRIEVE(state 复用),实际 {second['phase']!r}"
    )
    # turn_count 每个新 user turn 归 0:它是"单次 query() 闭环内"的轮数(防单次死循环
    # max_turns),不是会话累计量。跨轮累计是 bug——app.py:82 注释已坐实"turn_count 跨
    # 请求累计 → 超 max_turns 死锁"。messages/相位持久(GAP-B-1)但 turn_count/recovery
    # 预算每轮重置(app.py user-turn 重置块)。
    assert second["turn_count"] == 0, (
        f"turn_count 应每轮重置(防 max_turns 死锁),实际 {second['turn_count']}"
    )


@pytest.mark.asyncio
async def test_different_sessions_isolated(monkeypatch):
    """同 user 不同 session_id,State 独立(messages 不串)。"""
    from praxis2.server.app import make_app

    captured: list[dict] = []
    _install_inspect_query(monkeypatch, captured)

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)

    await _drive_chat_stream(app, cookie, message="hi-s1", session_id="s1")
    await _drive_chat_stream(app, cookie, message="hi-s2", session_id="s2")
    await deps.redis.aclose()

    # 两次都应是"开局":各自只有自己的 user msg,phase 各自为 None
    assert captured[0]["messages"] == [{"role": "user", "content": "hi-s1"}]
    assert captured[0]["phase"] is None
    assert captured[1]["messages"] == [{"role": "user", "content": "hi-s2"}]
    assert captured[1]["phase"] is None


@pytest.mark.asyncio
async def test_different_users_isolated(monkeypatch):
    """同 session_id 不同 user_id,State 独立(§11.6 多租户隔离,
    池 key 含 user_id,不串)。"""
    from praxis2.server.app import make_app

    captured: list[dict] = []
    _install_inspect_query(monkeypatch, captured)

    deps = make_test_app_deps()
    cookie_u1 = await preseed_session(deps, user_id="u1", email="u1@t.com")
    cookie_u2 = await preseed_session(deps, user_id="u2", email="u2@t.com")
    app = make_app(deps)

    await _drive_chat_stream(app, cookie_u1, message="from-u1", session_id="s1")
    await _drive_chat_stream(app, cookie_u2, message="from-u2", session_id="s1")
    await deps.redis.aclose()

    # 两次都应是开局:user_id 不同 → 池 key 不同 → State 不串
    assert captured[0]["messages"] == [{"role": "user", "content": "from-u1"}]
    assert captured[0]["phase"] is None
    assert captured[1]["messages"] == [{"role": "user", "content": "from-u2"}]
    assert captured[1]["phase"] is None


@pytest.mark.asyncio
async def test_session_pool_injected_into_app(monkeypatch):
    """_App 应注入 SessionPool 实例(默认 max_size=200, idle_ttl_s=3600)。"""
    from praxis2.runtime.session_pool import SessionPool
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    app = make_app(deps)
    inner = app._app
    assert hasattr(inner, "_session_pool"), "_App 应有 _session_pool 属性"
    assert isinstance(inner._session_pool, SessionPool)
    await deps.redis.aclose()
    # 避免 unused 警告
    _ = asyncio  # noqa: F841

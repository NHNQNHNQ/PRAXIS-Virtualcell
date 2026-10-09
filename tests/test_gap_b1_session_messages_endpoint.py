"""GAP-B-1 SP2:GET /api/me/sessions/{id} 返回 transcript user/assistant 文本。"""
from __future__ import annotations

import json as _json

import pytest

from praxis2.core.rmcp import Phase
from praxis2.memory.session import SessionEntry, SessionStore, record_phase_transition
from praxis2.server.app import make_app
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session


async def _get_messages(app, cookie, session_id):
    arrivals: list[bytes] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        if msg["type"] == "http.response.body" and msg.get("body"):
            arrivals.append(msg["body"])

    scope = {
        "type": "http", "method": "GET",
        "path": f"/api/me/sessions/{session_id}",
        "headers": [(b"cookie", cookie.encode())], "query_string": b"",
    }
    await app(scope, receive, send)
    return _json.loads(b"".join(arrivals))


async def _seed(ss, sid, uid="u1"):
    await ss.append_entry(SessionEntry(
        uuid="m1", type="user", content="问题", user_id=uid, session_id=sid))
    await ss.append_entry(SessionEntry(
        uuid="m2", type="assistant", content="答复", user_id=uid, session_id=sid))
    await ss.append_entry(SessionEntry(
        uuid="m3", type="assistant",
        content=[{"type": "tool_use", "id": "t", "name": "x", "input": {}}],
        user_id=uid, session_id=sid))
    await ss.append_entry(SessionEntry(
        uuid="m4", type="user",
        content=[{"type": "tool_result", "tool_use_id": "t", "content": "r"}],
        user_id=uid, session_id=sid))
    await record_phase_transition(
        ss, user_id=uid, session_id=sid, to=Phase.RETRIEVE, uuid_="ph")


@pytest.mark.asyncio
async def test_returns_text_filters_tool_and_phase():
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    ss = SessionStore(store)
    app._app._session_store = ss
    await _seed(ss, "s1")
    out = await _get_messages(app, cookie, "s1")
    await deps.redis.aclose()
    assert [(m["role"], m["text"]) for m in out["messages"]] == [
        ("user", "问题"), ("assistant", "答复"),
    ], f"实际 {out['messages']!r}"
    assert all("ts" in m for m in out["messages"])


@pytest.mark.asyncio
async def test_tenant_isolation():
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    _c1 = await preseed_session(deps, user_id="u1", email="u1@t.com")
    c2 = await preseed_session(deps, user_id="u2", email="u2@t.com")
    app = make_app(deps)
    ss = SessionStore(store)
    app._app._session_store = ss
    await _seed(ss, "s1", uid="u1")
    out2 = await _get_messages(app, c2, "s1")
    await deps.redis.aclose()
    assert out2["messages"] == [], f"u2 不应读到 u1 的会话,实际 {out2!r}"


@pytest.mark.asyncio
async def test_no_store_empty():
    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    assert app._app._session_store is None
    out = await _get_messages(app, cookie, "whatever")
    await deps.redis.aclose()
    assert out == {"messages": []}


@pytest.mark.asyncio
async def test_unauthenticated_401():
    """无 cookie(scope 无 user)→ 端点受保护,401。"""
    deps = make_test_app_deps()
    app = make_app(deps)
    status = {"v": 0}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        if msg["type"] == "http.response.start":
            status["v"] = msg["status"]

    scope = {
        "type": "http", "method": "GET", "path": "/api/me/sessions/s1",
        "headers": [], "query_string": b"",
    }
    await app(scope, receive, send)
    await deps.redis.aclose()
    assert status["v"] == 401, f"无 cookie 应 401,实际 {status['v']}"

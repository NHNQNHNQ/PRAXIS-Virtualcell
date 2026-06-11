"""GAP-B-1 Task 6:GET /api/me/sessions 列当前用户会话 + 多租户隔离 + 无 store。"""
from __future__ import annotations

import json as _json

import pytest

from praxis2.memory.session import SessionStore
from praxis2.server.app import make_app
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests._gap_b1_helpers import drive_chat, install_capture_query


async def _get_sessions(app, cookie):
    arrivals: list[bytes] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        if msg["type"] == "http.response.body" and msg.get("body"):
            arrivals.append(msg["body"])

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/me/sessions",
        "headers": [(b"cookie", cookie.encode())],
        "query_string": b"",
    }
    await app(scope, receive, send)
    return _json.loads(b"".join(arrivals))


@pytest.mark.asyncio
async def test_lists_user_sessions(monkeypatch):
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    app._app._session_store = SessionStore(store)
    install_capture_query(monkeypatch, [])
    await drive_chat(app, cookie, message="会话A首条", session_id="sa")
    await drive_chat(app, cookie, message="会话B首条", session_id="sb")
    out = await _get_sessions(app, cookie)
    await deps.redis.aclose()
    sids = {s["session_id"] for s in out["sessions"]}
    assert sids == {"sa", "sb"}, f"应列出两会话,实际 {out['sessions']!r}"
    previews = {s["preview"] for s in out["sessions"]}
    assert "会话A首条" in previews and "会话B首条" in previews


@pytest.mark.asyncio
async def test_tenant_isolation(monkeypatch):
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    c1 = await preseed_session(deps, user_id="u1", email="u1@t.com")
    c2 = await preseed_session(deps, user_id="u2", email="u2@t.com")
    app = make_app(deps)
    app._app._session_store = SessionStore(store)
    install_capture_query(monkeypatch, [])
    await drive_chat(app, c1, message="u1的会话", session_id="s1")
    out1 = await _get_sessions(app, c1)  # u1 查自己
    out2 = await _get_sessions(app, c2)  # u2 查
    await deps.redis.aclose()
    # 正向:u1 能看到自己的会话(防 vacuous——meta 若写错 user_id,u2 也会 [])
    assert [s["session_id"] for s in out1["sessions"]] == ["s1"], \
        f"u1 应看到自己的会话 s1,实际 {out1['sessions']!r}"
    # 隔离:u2 看不到 u1 的会话
    assert out2["sessions"] == [], f"u2 不应看到 u1 的会话,实际 {out2['sessions']!r}"


@pytest.mark.asyncio
async def test_no_store_returns_empty():
    deps = make_test_app_deps()  # 默认无 _pool → _session_store None
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    assert app._app._session_store is None
    out = await _get_sessions(app, cookie)
    await deps.redis.aclose()
    assert out == {"sessions": []}

"""GAP-B-1 Task 2:chat 路径 pool miss + 持久层可用 → resume 历史 transcript。"""
from __future__ import annotations

import pytest

from praxis2.memory.session import SessionEntry, SessionStore
from praxis2.server.app import make_app
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests._gap_b1_helpers import drive_chat, install_capture_query


@pytest.mark.asyncio
async def test_pool_miss_resumes_transcript(monkeypatch):
    """pool 无此 session,SessionStore 有历史 → resume 重建 messages;
    fake_query 看到的 state.messages 含历史 user/assistant + 本轮 user。"""
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    ss = SessionStore(store)
    app._app._session_store = ss  # 注入可用持久层(默认 FakeAuthRepo→None)
    # 预置历史 transcript(上一会话两条)
    await ss.append_entry(SessionEntry(
        uuid="h1", type="user", content="历史问题",
        user_id="u1", session_id="s1"))
    await ss.append_entry(SessionEntry(
        uuid="h2", type="assistant", content="历史回答",
        user_id="u1", session_id="s1"))
    captured: list = []
    install_capture_query(monkeypatch, captured)

    await drive_chat(app, cookie, message="新问题", session_id="s1")
    await deps.redis.aclose()

    assert captured[0]["messages"] == [
        {"role": "user", "content": "历史问题"},
        {"role": "assistant", "content": "历史回答"},
        {"role": "user", "content": "新问题"},
    ], f"resume 应重建历史 + 本轮 user,实际 {captured[0]['messages']!r}"


@pytest.mark.asyncio
async def test_no_store_empty_state_no_regression(monkeypatch):
    """SessionStore=None(默认无 PG)→ pool miss 走空 State(),仅本轮 user(零回归)。"""
    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    assert app._app._session_store is None
    captured: list = []
    install_capture_query(monkeypatch, captured)
    await drive_chat(app, cookie, message="hi", session_id="s-new")
    await deps.redis.aclose()
    assert captured[0]["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.asyncio
async def test_restart_resume_roundtrip(monkeypatch):
    """模拟重启:同一 store(权威持久层)新 app(pool 全新为空)→ 凭 session_id
    resume 出上一进程的历史。验收③后端能力 + 组件5 session_id round-trip。"""
    store = InMemoryStore()

    # 第一进程:一轮对话
    deps1 = make_test_app_deps(store=store)
    cookie1 = await preseed_session(deps1, user_id="u1")
    app1 = make_app(deps1)
    app1._app._session_store = SessionStore(store)
    install_capture_query(monkeypatch, [])
    await drive_chat(app1, cookie1, message="第一轮", session_id="s1")
    await deps1.redis.aclose()

    # "重启":新 deps/app 共享同一 store,pool 为空(SessionPool 不持久)
    deps2 = make_test_app_deps(store=store)
    cookie2 = await preseed_session(deps2, user_id="u1")
    app2 = make_app(deps2)
    app2._app._session_store = SessionStore(store)
    captured2: list = []
    install_capture_query(monkeypatch, captured2)
    await drive_chat(app2, cookie2, message="第二轮", session_id="s1")
    await deps2.redis.aclose()

    assert captured2[0]["messages"] == [
        {"role": "user", "content": "第一轮"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "第二轮"},
    ], f"重启后应凭 session_id resume 历史,实际 {captured2[0]['messages']!r}"

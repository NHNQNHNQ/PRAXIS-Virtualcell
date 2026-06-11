"""GAP-B-1 Task 3-5:每轮把 user / assistant delta / 相位变化落 transcript。"""
from __future__ import annotations

import pytest

from praxis2.memory.session import SessionStore
from praxis2.server.app import make_app
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests._gap_b1_helpers import drive_chat, install_capture_query


def _make_persistent_app(store):
    deps = make_test_app_deps(store=store)
    app = make_app(deps)
    app._app._session_store = SessionStore(store)
    return deps, app


@pytest.mark.asyncio
async def test_user_message_persisted(monkeypatch):
    """一轮 chat 后,transcript 含本轮 user entry。"""
    store = InMemoryStore()
    deps, app = _make_persistent_app(store)
    cookie = await preseed_session(deps, user_id="u1")
    install_capture_query(monkeypatch, [])
    await drive_chat(app, cookie, message="记住我", session_id="s1")
    await deps.redis.aclose()
    seq = await app._app._session_store.load_transcript(
        user_id="u1", session_id="s1")
    assert any(e.type == "user" and e.content == "记住我" for e in seq), \
        f"user 消息应落库,实际 {[(e.type, e.content) for e in seq]!r}"


@pytest.mark.asyncio
async def test_assistant_delta_persisted(monkeypatch):
    """query 产出的 assistant 消息(state.messages[prev_len:])落库,无重复 uuid。"""
    store = InMemoryStore()
    deps, app = _make_persistent_app(store)
    cookie = await preseed_session(deps, user_id="u1")
    install_capture_query(monkeypatch, [])  # fake_query append assistant "ok"
    await drive_chat(app, cookie, message="问", session_id="s1")
    await deps.redis.aclose()
    seq = await app._app._session_store.load_transcript(
        user_id="u1", session_id="s1")
    assert [e.type for e in seq] == ["user", "assistant"], \
        f"应含 user+assistant,实际 {[(e.type, e.content) for e in seq]!r}"
    assert seq[1].content == "ok"
    uuids = [e.uuid for e in seq]
    assert len(uuids) == len(set(uuids)), "uuid 不能重复"


@pytest.mark.asyncio
async def test_delta_user_persists_tool_result_skips_plain_text(monkeypatch):
    """delta 中 role=user:含 tool_result block → 持久;纯文本(stop_hook veto
    等合成消息)→ 跳过。防 resume 后假 user 消息污染历史(spec §123)。"""
    from praxis2.server import app as app_module

    store = InMemoryStore()
    deps, app = _make_persistent_app(store)
    cookie = await preseed_session(deps, user_id="u1")

    async def fake_query(
        state, *, client, registry, settings, runner, compactor, **_kw
    ):
        # 一轮:assistant(tool_use)→ user(tool_result,list)→ user(纯文本 veto)
        state.messages.append({"role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "x", "input": {}}]})
        state.messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]})
        state.messages.append({"role": "user", "content": "veto 纯文本"})
        yield {"type": "text", "text": "done"}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    await drive_chat(app, cookie, message="问", session_id="s1")
    await deps.redis.aclose()
    seq = await app._app._session_store.load_transcript(
        user_id="u1", session_id="s1")
    # user "问" + assistant(tool_use)+ user(tool_result)+ assistant(最终文本 done);
    # 纯文本 veto user 不入库(content 检查跳过)
    assert [e.type for e in seq] == ["user", "assistant", "user", "assistant"], \
        f"实际 {[(e.type, e.content) for e in seq]!r}"
    assert isinstance(seq[2].content, list), "第三条应是 tool_result 回合(list content)"
    assert seq[3].content == "done", "末条应是最终文本答复(chat 路径显式持久)"
    assert all(e.content != "veto 纯文本" for e in seq), "纯文本 veto user 不该持久"


@pytest.mark.asyncio
async def test_phase_transition_persisted_and_resumed(monkeypatch):
    """query 推进相位 → 落 phase-transition;新 State resume 后 rebuild_phase 恢复。"""
    from praxis2.core.rmcp import Phase, get_phase, set_phase
    from praxis2.core.state import State
    from praxis2.memory.session import resume
    from praxis2.server import app as app_module

    store = InMemoryStore()
    deps, app = _make_persistent_app(store)
    cookie = await preseed_session(deps, user_id="u1")

    async def fake_query(
        state, *, client, registry, settings, runner, compactor, **_kw
    ):
        set_phase(state, Phase.RETRIEVE)  # 模拟相位推进(初始 INIT → RETRIEVE)
        yield {"type": "text", "text": "ok"}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    await drive_chat(app, cookie, message="问", session_id="s1")
    seq = await app._app._session_store.load_transcript(
        user_id="u1", session_id="s1")
    assert any(
        e.type == "phase-transition" and e.phase == Phase.RETRIEVE.value
        for e in seq
    ), f"应落 phase-transition=retrieve,实际 {[(e.type, e.phase) for e in seq]!r}"

    st2 = State()
    await resume(app._app._session_store, st2, user_id="u1", session_id="s1")
    assert get_phase(st2) == Phase.RETRIEVE
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_delta_survives_reactive_compact(monkeypatch):
    """fake query append 本轮 assistant(tool_use)后模拟 reactive compact 截断
    state.messages(reassign,丢弃前段),本轮 assistant 仍经对象身份 diff 持久。
    旧 _prev_len 位置索引在此会越界空切片漏持久(query 前 len=1,compact 后
    messages[1:]=[]),id 追踪不漏——compact 缺陷的直接回归锚。"""
    from praxis2.server import app as app_module

    store = InMemoryStore()
    deps, app = _make_persistent_app(store)
    cookie = await preseed_session(deps, user_id="u1")

    async def fake_query(
        state, *, client, registry, settings, runner, compactor, **_kw
    ):
        # 本轮 append 一条 assistant(tool_use)——这是要持久的本轮新增
        state.messages.append({"role": "assistant", "content": [
            {"type": "tool_use", "id": "tc1", "name": "x", "input": {}}]})
        # 模拟 reactive compact:reassign 截断,只留尾段(含本轮 assistant);
        # 入口 messages=[user 问](query 前 len=1),此后 messages 变短到 len=1,
        # 使旧 _prev_len=1 的 messages[1:] 成空切片(漏),id-diff 不漏。
        state.messages = state.messages[-1:]
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    await drive_chat(app, cookie, message="问", session_id="s1")
    await deps.redis.aclose()
    seq = await app._app._session_store.load_transcript(
        user_id="u1", session_id="s1")
    # 本轮 user "问"(query 前持久,不受 compact 影响)
    assert any(e.type == "user" and e.content == "问" for e in seq), \
        f"user 应持久,实际 {[(e.type, e.content) for e in seq]!r}"
    # 关键:tool_use assistant(本轮新增对象)在 compact 截断后仍被 id-diff 持久
    tool_use_persisted = any(
        e.type == "assistant" and isinstance(e.content, list)
        and any(isinstance(b, dict) and b.get("type") == "tool_use"
                for b in e.content)
        for e in seq)
    assert tool_use_persisted, \
        f"compact 截断后 tool_use assistant 应仍持久,实际 {[(e.type, e.content) for e in seq]!r}"

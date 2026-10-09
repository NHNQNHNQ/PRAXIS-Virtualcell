from praxis2.core.compact import adjust_index_to_preserve_api_invariants
from praxis2.core.rmcp import Phase, get_phase
from praxis2.core.state import State
from praxis2.memory.extract import ExtractCandidate, persist_candidates
from praxis2.memory.review import list_pending
from praxis2.memory.session import (
    SessionEntry,
    SessionStore,
    record_phase_transition,
    resume,
)
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


async def test_inv5_session_roundtrip_restores_phase():
    # §5⑤#1:save→resume 往返,messages 结构等价(条数+tool 闭环对)+ 相位完整还原
    ss = SessionStore(InMemoryStore())
    await ss.append_entry(SessionEntry(uuid="u", type="user",
        content=[{"type": "text", "text": "原始任务"}],
        user_id="u1", session_id="s1"))
    await ss.append_entry(SessionEntry(uuid="a1", type="assistant",
        content=[{"type": "tool_use", "id": "t1", "name": "x", "input": {}}],
        user_id="u1", session_id="s1", parent_uuid="u"))
    await ss.append_entry(SessionEntry(uuid="r1", type="user",
        content=[{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}],
        user_id="u1", session_id="s1", parent_uuid="a1"))
    await record_phase_transition(ss, user_id="u1", session_id="s1",
                                  to=Phase.RETRIEVE, uuid_="p1", parent="r1")
    st = State()
    await resume(ss, st, user_id="u1", session_id="s1")
    assert get_phase(st) is Phase.RETRIEVE  # 相位完整还原
    # phase-transition 不入 messages → 仅 user+assistant+user(tool_result) 三条
    assert len(st.messages) == 3
    assert [m["role"] for m in st.messages] == ["user", "assistant", "user"]
    assert any("原始任务" in str(m["content"]) for m in st.messages)
    tus = {b["id"] for m in st.messages if m["role"] == "assistant"
           and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_use"}
    trs = {b["tool_use_id"] for m in st.messages if m["role"] == "user"
           and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_result"}
    assert tus == {"t1"} and trs == {"t1"}  # tool 闭环对结构完整,无孤儿


async def test_inv5_extract_idempotent():
    # §5⑤#2:学习闭环 extract 幂等
    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="session")
    c = ExtractCandidate(id="x1", text="经验", trigger="manual")
    await persist_candidates(store, ns, [c])
    await persist_candidates(store, ns, [c])
    assert len(await list_pending(store, ns)) == 1


def test_inv5_compact_never_splits_tool_pair():
    # §5⑤#3:compact 切点跨 tool_use/tool_result 对 → 调整后保留段无孤儿
    msgs = [
        {"role": "user", "content": "原始"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1",
                                           "name": "x", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                      "content": "r"}]},
        {"role": "assistant", "content": "答"},
    ]
    adj = adjust_index_to_preserve_api_invariants(msgs, 2)  # 切在 tool 对中间
    kept = msgs[adj:]
    tus = {b["id"] for m in kept if m["role"] == "assistant"
           and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_use"}
    trs = {b["tool_use_id"] for m in kept if m["role"] == "user"
           and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_result"}
    assert trs <= tus  # 无孤儿 tool_result(adjust_index 防)
    assert tus <= trs  # 无孤儿 tool_use(M1 相邻对落盘结构性杜绝,双向 API 安全)

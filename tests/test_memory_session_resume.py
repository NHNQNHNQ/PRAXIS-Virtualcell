from praxis2.core.rmcp import Phase, get_phase
from praxis2.core.state import State
from praxis2.memory.session import (
    SessionEntry,
    SessionStore,
    apply_preserved_segment_relinks,
    apply_snip_removals,
    record_phase_transition,
    recover_orphaned_parallel_tool_results,
    resume,
)
from praxis2.store.memory import InMemoryStore


def _e(u, parent=None, typ="user"):
    return SessionEntry(uuid=u, type=typ, content=u, user_id="u1", session_id="s1", parent_uuid=parent)


def test_snip_relinks_orphan_to_nearest_living_ancestor():

    seq = [_e("a"), _e("b", parent="x"), _e("c", parent="b")]
    fixed = apply_snip_removals(seq)
    assert [e.uuid for e in fixed] == ["a", "b", "c"]
    assert next(e for e in fixed if e.uuid == "b").parent_uuid == "a"
    assert next(e for e in fixed if e.uuid == "c").parent_uuid == "b"


def test_root_orphan_becomes_root():

    seq = [_e("a", parent="gone"), _e("b", parent="a")]
    fixed = apply_snip_removals(seq)
    assert fixed[0].parent_uuid is None


def _boundary(u, parent=None):
    return SessionEntry(
        uuid=u,
        type="system",
        content={"compact_boundary": True, "summary": "Previous summary"},
        user_id="u1",
        session_id="s1",
        parent_uuid=parent,
    )


def test_post_boundary_first_msg_relinks_to_boundary():

    seq = [_boundary("bnd"), _e("c", parent="old1"), _e("d", parent="c")]
    fixed = apply_preserved_segment_relinks(seq)
    assert next(e for e in fixed if e.uuid == "c").parent_uuid == "bnd"
    assert next(e for e in fixed if e.uuid == "d").parent_uuid == "c"


def test_no_boundary_is_noop():
    seq = [_e("a"), _e("b", parent="a")]
    fixed = apply_preserved_segment_relinks(seq)
    assert [e.parent_uuid for e in fixed] == [None, "a"]


def test_post_boundary_first_msg_not_orphan_keeps_parent():

    seq = [_e("a"), _boundary("bnd", parent="a"), _e("c", parent="a")]
    fixed = apply_preserved_segment_relinks(seq)
    assert next(e for e in fixed if e.uuid == "c").parent_uuid == "a"


def _asst_tooluse(u, ids, parent=None):
    return SessionEntry(
        uuid=u,
        type="assistant",
        content=[{"type": "tool_use", "id": i, "name": "t", "input": {}} for i in ids],
        user_id="u1",
        session_id="s1",
        parent_uuid=parent,
    )


def _user_toolresult(u, ids, parent=None):
    return SessionEntry(
        uuid=u,
        type="user",
        content=[{"type": "tool_result", "tool_use_id": i, "content": "ok"} for i in ids],
        user_id="u1",
        session_id="s1",
        parent_uuid=parent,
    )


def test_orphan_tool_result_dropped_and_missing_filled():
    seq = [
        _asst_tooluse("a", ["t1", "t2"]),
        _user_toolresult("b", ["t1", "t9"], parent="a"),
    ]
    msgs, needs_continue = recover_orphaned_parallel_tool_results(seq)
    res = [c for m in msgs if m["role"] == "user" for c in m["content"] if c.get("type") == "tool_result"]
    ids = sorted(c["tool_use_id"] for c in res)
    assert ids == ["t1", "t2"]
    assert any(c["tool_use_id"] == "t2" and c.get("is_error") for c in res)
    assert needs_continue is False


def test_unfinished_trailing_assistant_sets_needs_continue():
    seq = [_asst_tooluse("a", ["t1"])]
    msgs, needs_continue = recover_orphaned_parallel_tool_results(seq)
    assert needs_continue is True


def test_all_orphan_tool_results_produce_no_empty_user_message():

    seq = [
        _asst_tooluse("a", ["t1"]),
        _user_toolresult("b", ["t_orphan"], parent="a"),
    ]
    msgs, _ = recover_orphaned_parallel_tool_results(seq)
    assert all(m["content"] != [] for m in msgs)
    res = [
        c
        for m in msgs
        if m["role"] == "user" and isinstance(m["content"], list)
        for c in m["content"]
        if c.get("type") == "tool_result"
    ]
    assert any(c["tool_use_id"] == "t1" and c.get("is_error") for c in res)


async def test_save_resume_roundtrip_preserves_messages_and_phase():
    ss = SessionStore(InMemoryStore())
    await ss.append_entry(
        SessionEntry(
            uuid="u",
            type="user",
            content=[{"type": "text", "text": "\u539f\u59cb\u4efb\u52a1"}],
            user_id="u1",
            session_id="s1",
        )
    )
    await ss.append_entry(_asst_tooluse("a1", ["t1"], parent="u"))
    await ss.append_entry(_user_toolresult("r1", ["t1"], parent="a1"))
    await record_phase_transition(ss, user_id="u1", session_id="s1", to=Phase.RETRIEVE, uuid_="p1", parent="r1")
    st = State()
    rr = await resume(ss, st, user_id="u1", session_id="s1")
    assert rr.needs_continue is False
    assert get_phase(st) is Phase.RETRIEVE

    assert any("\u539f\u59cb\u4efb\u52a1" in str(m["content"]) for m in st.messages)
    tus = {
        b["id"]
        for m in st.messages
        if m["role"] == "assistant"
        for b in (m["content"] if isinstance(m["content"], list) else [])
        if isinstance(b, dict) and b.get("type") == "tool_use"
    }
    trs = {
        b["tool_use_id"]
        for m in st.messages
        if m["role"] == "user"
        for b in (m["content"] if isinstance(m["content"], list) else [])
        if isinstance(b, dict) and b.get("type") == "tool_result"
    }
    assert trs <= tus


async def test_resume_unfinished_injects_continue():
    ss = SessionStore(InMemoryStore())
    await ss.append_entry(SessionEntry(uuid="u", type="user", content="q", user_id="u1", session_id="s1"))
    await ss.append_entry(_asst_tooluse("a1", ["t1"], parent="u"))
    st = State()
    rr = await resume(ss, st, user_id="u1", session_id="s1")
    assert rr.needs_continue is True
    assert any("continue" in str(m["content"]) for m in st.messages)

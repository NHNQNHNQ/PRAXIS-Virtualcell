import pytest

from praxis2.core.rmcp import Phase, get_phase
from praxis2.core.state import State
from praxis2.memory.session import (
    SessionEntry,
    SessionStore,
    rebuild_phase,
    record_phase_transition,
)
from praxis2.store.memory import InMemoryStore


def _entry(uuid_, typ="user", content="hi", parent=None):
    return SessionEntry(
        uuid=uuid_,
        type=typ,
        content=content,
        parent_uuid=parent,
        session_id="s1",
        user_id="u1",
    )


async def test_append_then_load_roundtrip_ordered():
    ss = SessionStore(InMemoryStore())
    await ss.append_entry(_entry("a"))
    await ss.append_entry(_entry("b", parent="a"))
    seq = await ss.load_transcript(user_id="u1", session_id="s1")
    assert [e.uuid for e in seq] == ["a", "b"]
    assert seq[1].parent_uuid == "a"


async def test_append_is_idempotent_on_duplicate_uuid():
    ss = SessionStore(InMemoryStore())
    await ss.append_entry(_entry("a", content="first"))
    await ss.append_entry(_entry("a", content="dup-should-be-ignored"))
    seq = await ss.load_transcript(user_id="u1", session_id="s1")
    assert len(seq) == 1 and seq[0].content == "first"


async def test_illegal_type_rejected():
    ss = SessionStore(InMemoryStore())
    with pytest.raises(ValueError, match="type"):
        await ss.append_entry(_entry("a", typ="progress"))


async def test_load_unknown_session_returns_empty():
    ss = SessionStore(InMemoryStore())
    assert await ss.load_transcript(user_id="u1", session_id="nope") == []


async def test_phase_transition_persisted_and_rebuilt_from_last():
    ss = SessionStore(InMemoryStore())
    await ss.append_entry(_entry("a"))
    await record_phase_transition(ss, user_id="u1", session_id="s1", to=Phase.RETRIEVE, uuid_="p1", parent="a")
    await record_phase_transition(ss, user_id="u1", session_id="s1", to=Phase.ANTI_FILTER, uuid_="p2", parent="p1")
    st = State()
    await rebuild_phase(ss, st, user_id="u1", session_id="s1")
    assert get_phase(st) is Phase.ANTI_FILTER


async def test_rebuild_phase_no_transition_stays_init():
    ss = SessionStore(InMemoryStore())
    await ss.append_entry(_entry("a"))
    st = State()
    await rebuild_phase(ss, st, user_id="u1", session_id="s1")
    assert get_phase(st) is Phase.INIT

from praxis2.core.seams import (
    AllowAllPermission,
    MinimalCompactor,
    PermissionDecision,
)
from praxis2.core.state import State


def test_allow_all_permission_allows():
    res = AllowAllPermission().check(tool=None, payload={}, state=State())
    assert res.decision is PermissionDecision.ALLOW
    assert res.reason is None


async def test_minimal_compactor_drops_old_keeps_recent_no_orphan():
    s = State()

    s.messages = [
        {"role": "user", "content": "q0"},
        {"role": "assistant", "content": "a0"},
        {"role": "user", "content": "q1"},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "tu1", "name": "t", "input": {}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "tu1", "is_error": False, "content": "r"},
            ],
        },
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "q3"},
        {"role": "assistant", "content": "a3"},
    ]
    before = len(s.messages)
    await MinimalCompactor().compact(s)
    assert len(s.messages) < before
    assert s.transition == "reactive_compact"

    tu_ids = {
        b["id"]
        for m in s.messages
        if isinstance(m["content"], list)
        for b in m["content"]
        if b.get("type") == "tool_use"
    }
    tr_ids = {
        b["tool_use_id"]
        for m in s.messages
        if isinstance(m["content"], list)
        for b in m["content"]
        if b.get("type") == "tool_result"
    }
    assert tr_ids <= tu_ids


async def test_minimal_compactor_noop_on_short_history():
    s = State()
    s.messages = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
    await MinimalCompactor().compact(s)
    assert len(s.messages) == 2

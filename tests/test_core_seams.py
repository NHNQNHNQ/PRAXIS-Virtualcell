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
    # 8 条:user/assistant 交替,中段含一对 tool_use/tool_result(跨界要保护)
    s.messages = [
        {"role": "user", "content": "q0"},
        {"role": "assistant", "content": "a0"},
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "tu1", "name": "t", "input": {}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tu1", "is_error": False, "content": "r"},
        ]},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "q3"},
        {"role": "assistant", "content": "a3"},
    ]
    before = len(s.messages)
    await MinimalCompactor().compact(s)
    assert len(s.messages) < before  # 确实压缩了
    assert s.transition == "reactive_compact"
    # 不变量:保留段里每个 tool_result 都能找到同段内对应 tool_use(无孤儿)
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
    assert tr_ids <= tu_ids  # 每个 tool_result 有对应 tool_use


async def test_minimal_compactor_noop_on_short_history():
    s = State()
    s.messages = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
    await MinimalCompactor().compact(s)
    assert len(s.messages) == 2  # 太短不压

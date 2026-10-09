from praxis2.core.compact import adjust_index_to_preserve_api_invariants


def _asst(ids):
    return {"role": "assistant", "content": [{"type": "tool_use", "id": i, "name": "t", "input": {}} for i in ids]}


def _res(ids):
    return {"role": "user", "content": [{"type": "tool_result", "tool_use_id": i, "content": "x"} for i in ids]}


def test_cut_moved_back_to_include_matching_tool_use():

    msgs = [_asst(["t1"]), _res(["t1"]), {"role": "user", "content": "next"}]
    adj = adjust_index_to_preserve_api_invariants(msgs, 1)
    assert adj == 0
    kept = msgs[adj:]
    tus = {b["id"] for m in kept if m["role"] == "assistant" for b in m["content"] if b["type"] == "tool_use"}
    trs = {
        b["tool_use_id"]
        for m in kept
        if m["role"] == "user" and isinstance(m["content"], list)
        for b in m["content"]
        if b.get("type") == "tool_result"
    }
    assert trs <= tus


def test_clean_cut_unchanged():
    msgs = [{"role": "user", "content": "a"}, _asst(["t1"]), _res(["t1"])]
    assert adjust_index_to_preserve_api_invariants(msgs, 1) == 1


def test_cut_at_zero_or_end_safe():
    msgs = [_asst(["t1"]), _res(["t1"])]
    assert adjust_index_to_preserve_api_invariants(msgs, 0) == 0
    assert adjust_index_to_preserve_api_invariants(msgs, 2) == 2


def test_parallel_tools_cut_moved_back():

    msgs = [_asst(["t1", "t2"]), _res(["t1", "t2"]), {"role": "user", "content": "next"}]
    adj = adjust_index_to_preserve_api_invariants(msgs, 1)
    assert adj == 0
    kept = msgs[adj:]
    tus = {b["id"] for m in kept if m["role"] == "assistant" for b in m["content"] if b["type"] == "tool_use"}
    trs = {
        b["tool_use_id"]
        for m in kept
        if m["role"] == "user" and isinstance(m["content"], list)
        for b in m["content"]
        if b.get("type") == "tool_result"
    }
    assert trs <= tus


def test_multi_pair_cut_stops_at_clean_nonzero_index():

    msgs = [
        {"role": "user", "content": "q"},  # 0
        _asst(["t1"]),  # 1
        _res(["t1"]),  # 2
        _asst(["t2"]),  # 3
        _res(["t2"]),  # 4
    ]
    adj = adjust_index_to_preserve_api_invariants(msgs, 4)
    assert adj == 3
    kept = msgs[adj:]
    tus = {b["id"] for m in kept if m["role"] == "assistant" for b in m["content"] if b["type"] == "tool_use"}
    trs = {
        b["tool_use_id"]
        for m in kept
        if m["role"] == "user" and isinstance(m["content"], list)
        for b in m["content"]
        if b.get("type") == "tool_result"
    }
    assert trs <= tus

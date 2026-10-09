from praxis2.core.compact import adjust_index_to_preserve_api_invariants


def _asst(ids):
    return {"role": "assistant",
            "content": [{"type": "tool_use", "id": i, "name": "t", "input": {}}
                        for i in ids]}


def _res(ids):
    return {"role": "user",
            "content": [{"type": "tool_result", "tool_use_id": i, "content": "x"}
                        for i in ids]}


def test_cut_moved_back_to_include_matching_tool_use():
    # 切点落在 tool_use(idx0)与 tool_result(idx1)之间 → 必须前移含 idx0
    msgs = [_asst(["t1"]), _res(["t1"]), {"role": "user", "content": "next"}]
    adj = adjust_index_to_preserve_api_invariants(msgs, 1)
    assert adj == 0  # 前移到含 tool_use 的轮
    kept = msgs[adj:]
    tus = {b["id"] for m in kept if m["role"] == "assistant"
           for b in m["content"] if b["type"] == "tool_use"}
    trs = {b["tool_use_id"] for m in kept if m["role"] == "user"
           and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_result"}
    assert trs <= tus  # 无孤儿


def test_clean_cut_unchanged():
    msgs = [{"role": "user", "content": "a"}, _asst(["t1"]), _res(["t1"])]
    assert adjust_index_to_preserve_api_invariants(msgs, 1) == 1  # 切点干净不动


def test_cut_at_zero_or_end_safe():
    msgs = [_asst(["t1"]), _res(["t1"])]
    assert adjust_index_to_preserve_api_invariants(msgs, 0) == 0
    assert adjust_index_to_preserve_api_invariants(msgs, 2) == 2


def test_parallel_tools_cut_moved_back():
    # §5⑤ 并行多 tool_use/result:同轮多 tool,切点在 use|result 之间 → 前移含整 use 轮
    msgs = [_asst(["t1", "t2"]), _res(["t1", "t2"]),
            {"role": "user", "content": "next"}]
    adj = adjust_index_to_preserve_api_invariants(msgs, 1)
    assert adj == 0
    kept = msgs[adj:]
    tus = {b["id"] for m in kept if m["role"] == "assistant"
           for b in m["content"] if b["type"] == "tool_use"}
    trs = {b["tool_use_id"] for m in kept if m["role"] == "user"
           and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_result"}
    assert trs <= tus  # 并行对也无孤儿


def test_multi_pair_cut_stops_at_clean_nonzero_index():
    # §5⑤ 两对串行 tool 对:切点落第二对 use|result 之间 → 回退一步停在含 t2 use 轮(非 0)
    msgs = [
        {"role": "user", "content": "q"},      # 0
        _asst(["t1"]),                          # 1
        _res(["t1"]),                           # 2
        _asst(["t2"]),                          # 3
        _res(["t2"]),                           # 4
    ]
    adj = adjust_index_to_preserve_api_invariants(msgs, 4)
    assert adj == 3  # 回退一步到含 t2 tool_use 轮,停在非零(不过度回退到 0)
    kept = msgs[adj:]
    tus = {b["id"] for m in kept if m["role"] == "assistant"
           for b in m["content"] if b["type"] == "tool_use"}
    trs = {b["tool_use_id"] for m in kept if m["role"] == "user"
           and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_result"}
    assert trs <= tus

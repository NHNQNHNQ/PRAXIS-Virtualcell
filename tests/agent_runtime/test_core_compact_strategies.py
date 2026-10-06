
from praxis2.core.compact import AutoCompactor, MicroCompactor
from praxis2.core.state import State
from ._llm_fakes import TURN_COMPACT_SUMMARY, FakeLLMClient


class _S:
    model = "m"
    max_tokens = 256
    compact_keep_recent = 2  # 重注保留最近 N 条


async def test_autocompact_summarizes_keeps_pinned_task_and_recent():
    client = FakeLLMClient(turns=[TURN_COMPACT_SUMMARY])
    st = State()
    st.messages = [
        {"role": "user", "content": "原始任务:做 X"},          # idx0 = pinned
        {"role": "assistant", "content": "中间思考1"},
        {"role": "user", "content": "中间观察2"},
        {"role": "assistant", "content": "中间思考3"},
        {"role": "user", "content": "最近1"},
        {"role": "assistant", "content": "最近2"},
    ]
    st.original_task_idx = 0
    await AutoCompactor(client, _S()).compact(st)
    txt = str(st.messages)
    assert "原始任务:做 X" in txt          # §12.3 原始指令 pinned 不丢
    assert "前段摘要" in txt                # API 总结成 boundary
    assert "最近2" in txt                   # 最近 N 条保留
    assert "中间思考1" not in txt           # 中间被压
    await client.aclose()


async def test_autocompact_circuit_breaker_gives_up_after_failures():
    client = FakeLLMClient(turns=[TURN_COMPACT_SUMMARY])
    st = State()
    st.messages = [{"role": "user", "content": f"m{i}"} for i in range(8)]
    st.original_task_idx = 0
    st.auto_compact_tracking["consecutive_failures"] = 3  # 已达熔断阈值
    before = list(st.messages)
    await AutoCompactor(client, _S()).compact(st)
    assert st.messages == before  # 熔断:放弃压缩,原样返回不抛
    await client.aclose()


async def test_autocompact_no_orphaned_tool_pair_across_boundary():
    # §5⑤/§7.4.5★ 接入:保留尾切点落 tool 对中间 → adjust_index 前移,重注后无孤儿
    client = FakeLLMClient(turns=[TURN_COMPACT_SUMMARY])
    st = State()
    st.messages = [
        {"role": "user", "content": "原始任务"},                                    # 0
        {"role": "assistant", "content": "中间"},                                    # 1
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1",
                                           "name": "x", "input": {}}]},               # 2
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                      "content": "r"}]},                              # 3
        {"role": "assistant", "content": "答"},                                       # 4
    ]
    st.original_task_idx = 0
    # keep=2 → 初始 cut=3 落 tool_use(2)|tool_result(3) 之间 → adjust 前移到 2
    await AutoCompactor(client, _S()).compact(st)
    assert "前段摘要" in str(st.messages)
    assert "中间" not in str(st.messages)
    tus = {b["id"] for m in st.messages if m["role"] == "assistant"
           and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_use"}
    trs = {b["tool_use_id"] for m in st.messages if m["role"] == "user"
           and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_result"}
    assert trs <= tus  # 无孤儿 tool_result(adjust_index 防,§7.4.5★)
    assert tus <= trs  # 无孤儿 tool_use(上游 M1 相邻对落盘结构性杜绝,双向安全)
    await client.aclose()


async def test_autocompact_ptl_defense_truncates_and_retries_once():
    # §7.4.5 PTL 防御:首次总结失败 → 截断历史重试一次成功 → 不计熔断、压缩完成

    class _PtlThenSuccess:
        """首次抛"prompt is too long"异常,第二次正常 yield TURN_COMPACT_SUMMARY。"""
        def __init__(self):
            self._called = 0
            self.call_count = 0

        async def stream_messages(self, **kwargs):
            self._called += 1
            self.call_count += 1
            if self._called == 1:
                raise RuntimeError("prompt is too long")
                yield  # 保持 async generator(unreachable)
            for ev in TURN_COMPACT_SUMMARY:
                yield ev

        async def aclose(self):
            pass

    client = _PtlThenSuccess()
    st = State()
    st.messages = [{"role": "user", "content": f"m{i}"} for i in range(8)]
    st.original_task_idx = 0
    await AutoCompactor(client, _S()).compact(st)
    assert client.call_count == 2  # 首次失败 + 截断重试各一次
    assert "前段摘要" in str(st.messages)  # 重试成功 → 压缩完成
    assert st.auto_compact_tracking["consecutive_failures"] == 0  # 不计熔断
    await client.aclose()


async def test_autocompact_no_duplicate_pin_when_task_in_retained():
    # §12.3:original_task_idx 已在保留段(>=cut)→ 不重复 pin(原始任务不出现两次)
    client = FakeLLMClient(turns=[TURN_COMPACT_SUMMARY])
    st = State()
    st.messages = [
        {"role": "user", "content": "中间1"},
        {"role": "assistant", "content": "中间2"},
        {"role": "user", "content": "原始任务在尾部"},   # idx2,落保留段
        {"role": "assistant", "content": "最近"},
    ]
    st.original_task_idx = 2  # keep=2 → cut=2,idx2>=cut → 不重复 pin
    await AutoCompactor(client, _S()).compact(st)
    assert "前段摘要" in str(st.messages)
    cnt = sum("原始任务在尾部" in str(m["content"]) for m in st.messages)
    assert cnt == 1  # 仅在保留尾段出现一次,未被额外 pin 到最前
    await client.aclose()


def test_microcompact_clears_old_tool_results_keeps_structure():
    st = State()
    st.messages = [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1",
                                           "name": "read", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                      "content": "巨大的旧文件内容" * 50}]},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t2",
                                           "name": "read", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t2",
                                      "content": "最近结果,保留"}]},
    ]
    MicroCompactor(max_age_turns=1).compact_local(st)
    # 旧 t1 结果被清成占位,结构/ id 保留;t2 最近的不动
    t1 = st.messages[1]["content"][0]
    t2 = st.messages[3]["content"][0]
    assert t1["tool_use_id"] == "t1" and "cleared" in t1["content"]
    assert "巨大的旧文件内容" not in str(st.messages)
    assert t2["content"] == "最近结果,保留"

from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import (
    TURN_AFTER_TOOL,
    TURN_BOOM_TOOL,
    TURN_TOOLUSE,
    FakeLLMClient,
)


class Echo(Tool):
    name = "echo"

    def input_schema(self):
        return {"type": "object", "properties": {"t": {"type": "string"}}}

    async def run(self, payload):
        return ToolResult(ok=True, value=payload["t"])


class Boom(Tool):
    name = "boom"

    def input_schema(self):
        return {"type": "object", "properties": {}}

    async def run(self, payload):
        return ToolResult(ok=False, error="炸了", recovery_hint="装 X 后重试")


_API_TOOL_RESULT_KEYS = {"type", "tool_use_id", "content", "is_error"}


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


async def test_two_turn_closed_loop_tool_then_final_answer():
    reg = ToolRegistry()
    reg.register(Echo())
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    # turn 1: tool_use → turn 2: 终答
    client = FakeLLMClient(turns=[TURN_TOOLUSE, TURN_AFTER_TOOL])
    st = State()
    st.messages = [{"role": "user", "content": "查 hi"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
            system="助手",
        )
    ]
    types = [e["type"] for e in events]
    # 闭环:tool_use → tool_result → 终答 text → end(STOP)
    assert types == ["text", "tool_use", "tool_result", "text", "end"]
    tr = next(e for e in events if e["type"] == "tool_result")
    assert tr["is_error"] is False and tr["content"] == "hi"
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    # messages 链路:user / assistant(tool_use) / user(tool_result) / 终答轮
    assert st.messages[1]["role"] == "assistant"
    assert st.messages[1]["content"][0]["type"] == "tool_use"
    assert st.messages[2]["role"] == "user"
    assert st.messages[2]["content"][0]["type"] == "tool_result"
    assert st.turn_count == 2  # tool 轮 + 终答轮
    await client.aclose()


async def test_max_turns_terminates_when_model_keeps_calling_tools():
    # §7.1.1:模型每轮都发 tool_use 时,maxTurns 必须能终止(且不在循环顶误中断)
    reg = ToolRegistry()
    reg.register(Echo())
    runner = SerialToolRunner(reg, recovery_budget=99, permission=AllowAllPermission())
    # 无限 tool_use — FakeLLMClient 超 turn 后默认 stop,但 max_turns=3 会先兜住
    # 给够 turns 避免 FakeLLMClient 耗尽前 maxTurns 先触发
    client = FakeLLMClient(turns=[TURN_TOOLUSE] * 10)

    class S:
        model = "m"
        max_tokens = 64
        max_turns = 3
        recovery_budget = 99
        max_output_recovery = 2

    st = State()
    st.messages = [{"role": "user", "content": "循环吧"}]
    last = None
    async for e in query(
        st,
        client=client,
        registry=reg,
        settings=S(),
        runner=runner,
        compactor=MinimalCompactor(),
    ):
        last = e
    assert last == {"type": "end", "reason": TerminalReason.MAX_TURNS.value}
    assert st.turn_count >= 3  # 顶部硬顶在第 max_turns 轮拦截(详见 Step 3)
    await client.aclose()


async def test_error_tool_result_serialized_api_valid_with_folded_content():
    # 总纲 §7.3.7★:落 messages 的 tool_result 只能含 4 个 API 合法键;
    # diagnostics/recovery_hint/recovery_budget_remaining 折叠进 content(模型可见 §4②)
    reg = ToolRegistry()
    reg.register(Boom())
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    # turn 1: boom tool_use → turn 2: 终答
    client = FakeLLMClient(turns=[TURN_BOOM_TOOL, TURN_AFTER_TOOL])
    st = State()
    st.messages = [{"role": "user", "content": "干活"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
        )
    ]
    tr_msg = next(
        m
        for m in st.messages
        if m["role"] == "user"
        and isinstance(m["content"], list)
        and m["content"]
        and m["content"][0].get("type") == "tool_result"
    )
    block = tr_msg["content"][0]
    assert set(block.keys()) == _API_TOOL_RESULT_KEYS  # 仅 4 个 API 合法键
    assert block["is_error"] is True
    assert "装 X 后重试" in block["content"]  # recovery_hint 折叠进 content(§4②)
    assert "[剩余自主恢复预算]" in block["content"]  # budget 也折叠(is not None 分支)
    # SSE yield 的事件仍是富结构(可观测层不丢字段)
    yielded = next(e for e in events if e["type"] == "tool_result")
    assert yielded["recovery_hint"] == "装 X 后重试"
    await client.aclose()

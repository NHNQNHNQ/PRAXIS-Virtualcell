from praxis2.core.query import AbortSignal, query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import TURN_TOOLUSE, FakeLLMClient


class Echo(Tool):
    name = "echo"

    def input_schema(self):
        return {"type": "object", "properties": {"t": {"type": "string"}}}

    async def run(self, payload):
        return ToolResult(ok=True, value=payload["t"])


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


async def test_abort_after_stream_pairs_tooluse_and_returns_aborted():
    reg = ToolRegistry()
    reg.register(Echo())
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    client = FakeLLMClient(turns=[TURN_TOOLUSE])
    abort = AbortSignal()
    abort.set()
    st = State()
    st.messages = [{"role": "user", "content": "\u67e5 hi"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
            abort=abort,
        )
    ]
    assert events[-1] == {"type": "end", "reason": TerminalReason.ABORTED.value}

    asst = next(m for m in st.messages if m["role"] == "assistant" and isinstance(m["content"], list))
    tu_ids = {b["id"] for b in asst["content"] if b["type"] == "tool_use"}
    user_tr = next(
        m
        for m in st.messages
        if m["role"] == "user"
        and isinstance(m["content"], list)
        and any(b.get("type") == "tool_result" for b in m["content"])
    )
    tr_ids = {b["tool_use_id"] for b in user_tr["content"] if b["type"] == "tool_result"}
    assert tu_ids and tu_ids == tr_ids
    await client.aclose()

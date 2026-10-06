from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from ._llm_fakes import TURN_BOOM_TOOL, TURN_FINAL_TEXT, FakeLLMClient


class Boom(Tool):
    name = "boom"

    def input_schema(self):
        return {"type": "object", "properties": {}}

    async def run(self, payload):
        return ToolResult(ok=False, error="炸了:依赖 X 缺失", recovery_hint="装 X 后重试")


def _reg_runner(budget):
    reg = ToolRegistry()
    reg.register(Boom())
    return reg, SerialToolRunner(reg, recovery_budget=budget, permission=AllowAllPermission())


class _S:
    model = "m"
    max_tokens = 64
    max_turns = 50
    recovery_budget = 2
    max_output_recovery = 2


async def test_failing_tool_loop_continues_not_stop_and_counts_recovery():
    # §4/§5③:工具失败 → tool_result(is_error) 回喂、循环*继续*(不停下问人)。
    # budget=3 > 2 次失败,故不升级;模型第 3 次给终答 → STOP,证明循环没停下问人。
    reg, runner = _reg_runner(budget=3)

    class S3:
        model = "m"
        max_tokens = 64
        max_turns = 50
        recovery_budget = 3  # 升级阈值 > 本测试的 2 次失败,故走到终答而非 ESCALATED
        max_output_recovery = 2

    # 第1次 tool_use(boom 失败)→ 第2次模型仍发 tool_use(继续尝试)→ 第3次终答
    client = FakeLLMClient(turns=[TURN_BOOM_TOOL, TURN_BOOM_TOOL, TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "干活"}]
    events = [
        e async for e in query(
            st, client=client, registry=reg, settings=S3(),
            runner=runner, compactor=MinimalCompactor(),
        )
    ]
    # 关键断言:出现了 is_error 的 tool_result,且循环继续到拿到终答 STOP(没有停下问人)
    err_results = [e for e in events if e["type"] == "tool_result" and e["is_error"]]
    assert len(err_results) >= 1
    assert err_results[0]["recovery_hint"] == "装 X 后重试"
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert st.recovery_attempts == 2  # 两轮失败工具各计 1
    await client.aclose()


async def test_recovery_budget_exhausted_escalates():
    # 预算耗尽且模型仍不终答 → ESCALATED(对应模型应主动 ask_user;此为可测代理)
    reg, runner = _reg_runner(budget=2)
    # 模型一直发 boom tool_use,足够触发预算耗尽(多备几轮)
    client = FakeLLMClient(turns=[TURN_BOOM_TOOL] * 10)
    st = State()
    st.messages = [{"role": "user", "content": "干活"}]
    last = None
    async for e in query(
        st, client=client, registry=reg, settings=_S(),
        runner=runner, compactor=MinimalCompactor(),
    ):
        last = e
    assert last == {"type": "end", "reason": TerminalReason.ESCALATED.value}
    assert st.recovery_attempts >= 2  # 达到/超过预算才升级
    await client.aclose()

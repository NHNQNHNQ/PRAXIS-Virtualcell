"""GAP-AH 三件套查询级集成测试。

验证三项反幻觉行为在 query() + SerialToolRunner 真路径下组合正确:
(a) premature SkillExec(无检索)→ RetrieveFirstPermission DENY
(b) BrainQuery 真命中 → advance_phase_on_real_retrieval post_hook 推进相位 → 后续 SkillExec ALLOW
(c) 声称执行但零工具证据 → make_tool_use_presence_stop_hook veto 一次
"""

from praxis2.core.query import query
from praxis2.core.rmcp import Phase, get_phase
from praxis2.core.seams import MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.hooks.builtin import (
    advance_phase_on_real_retrieval,
    make_tool_use_presence_stop_hook,
)
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.bash_policy import BashCommandPolicy
from praxis2.tools.permission import RetrieveFirstPermission
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import FakeLLMClient


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


class _FakeBrainQuery(Tool):
    """模拟 BrainQuery 真命中(设 last_retrieval_real_hit,供推进 post_hook 读)。"""

    name = "BrainQuery"
    rmcp_op = None  # 检索类,不受相位约束

    def input_schema(self):
        return {"type": "object"}

    async def run(self, payload):
        self.last_retrieval_real_hit = True  # 标记真命中
        return ToolResult(ok=True, value={"hits": [{"slug": "x"}], "source": "filesystem"})


class _FakeSkill(Tool):
    name = "SkillExec"
    rmcp_op = "call_skill"  # 执行类,受相位/证据门约束

    def input_schema(self):
        return {"type": "object"}

    async def run(self, payload):
        return ToolResult(ok=True, value={"result": "docked"})


def _turn_tool_use(tid, name):
    """构造 LLM 单轮工具调用事件序列。"""
    return [
        {"type": "text", "text": ""},
        {"type": "tool_use", "id": tid, "name": name, "input": {}},
        {"type": "message_stop", "stop_reason": "tool_use", "usage": {}},
    ]


def _turn_final(text):
    """构造 LLM 单轮终答事件序列。"""
    return [
        {"type": "text", "text": text},
        {"type": "message_stop", "stop_reason": "end_turn", "usage": {}},
    ]


def _runner():
    """构造含 RetrieveFirstPermission + advance_phase_on_real_retrieval 的 runner。"""
    reg = ToolRegistry()
    reg.register(_FakeBrainQuery())
    reg.register(_FakeSkill())
    # RetrieveFirstPermission 包装 BashCommandPolicy:非 Bash 工具全透传,
    # 再由 RetrieveFirstPermission 按相位决定 SkillExec 能否放行
    perm = RetrieveFirstPermission(BashCommandPolicy())
    runner = SerialToolRunner(
        reg,
        recovery_budget=3,
        permission=perm,
        post_hooks=[advance_phase_on_real_retrieval],
    )
    return reg, runner


async def test_premature_execute_denied_then_retrieve_unlocks():
    """(a)+(b) 组合:未检索前 SkillExec 被拒,BrainQuery 真命中后相位推进,SkillExec 放行。

    LLM 脚本:
    1) 调 SkillExec(tu1)→ DENY(相位 INIT,证据门未过)
    2) 调 BrainQuery(tu2)→ 成功,post_hook 推进 INIT→RETRIEVE
    3) 调 SkillExec(tu3)→ ALLOW(相位已过 INIT)
    4) 终答"完成"
    """
    reg, runner = _runner()
    client = FakeLLMClient(turns=[
        _turn_tool_use("tu1", "SkillExec"),
        _turn_tool_use("tu2", "BrainQuery"),
        _turn_tool_use("tu3", "SkillExec"),
        _turn_final("完成"),
    ])
    st = State()
    st.messages = [{"role": "user", "content": "对接 imatinib 到 1iep"}]

    events = [e async for e in query(
        st,
        client=client,
        registry=reg,
        settings=_settings(),
        runner=runner,
        compactor=MinimalCompactor(),
    )]

    # 取所有 tool_result 事件
    tool_results = [e for e in events if e.get("type") == "tool_result"]

    # (a) 验证:第一次 SkillExec 因证据门被拒
    assert any(
        e.get("is_error") and "检索先行" in (e.get("content") or "")
        for e in tool_results
    ), f"未检索的 SkillExec 应被证据门拒;实际 tool_results={tool_results}"

    # (b) 验证:BrainQuery 成功推进相位,不再是 INIT
    assert get_phase(st) is not Phase.INIT, (
        f"BrainQuery 真命中后相位应推进出 INIT,实际={get_phase(st)}"
    )

    # (b) 验证:检索后 SkillExec(tu3)被放行(有非错误的 tool_result)
    assert any(
        not e.get("is_error") for e in tool_results
    ), f"检索后 SkillExec 应放行(有非 is_error 的 tool_result);实际={tool_results}"

    # 终态正常结束
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}

    await client.aclose()


async def test_claim_without_tools_vetoed_then_stops():
    """(c) 验证:终答声称已执行(含亲和力断言)但零工具证据 → veto 一次,再走一轮后放行。

    LLM 脚本:两轮终答(均含执行声称);stop_hook 首轮 veto 后 veto_count=1 不再拦,
    第二轮正常放行 → STOP。
    """
    reg, runner = _runner()
    claim_text = "我已对接完成,最佳亲和力 -9.2 kcal/mol。"
    client = FakeLLMClient(turns=[
        _turn_final(claim_text),
        _turn_final(claim_text),
    ])
    st = State()
    st.messages = [{"role": "user", "content": "对接并给分"}]

    events = [e async for e in query(
        st,
        client=client,
        registry=reg,
        settings=_settings(),
        runner=runner,
        compactor=MinimalCompactor(),
        stop_hook=make_tool_use_presence_stop_hook(),
    )]

    # (c) 验证:veto 恰好发生一次
    assert st.stop_hook_veto_count == 1, (
        f"应 veto 一次,实际 veto_count={st.stop_hook_veto_count}"
    )

    # (c) 验证:注入了包含"反幻觉否决"的 user 消息
    assert any(
        m["role"] == "user" and "反幻觉否决" in str(m.get("content", ""))
        for m in st.messages
    ), f"应注入反幻觉否决 user 消息;messages={st.messages}"

    # 最终正常终止
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}

    await client.aclose()

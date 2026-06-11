
from praxis2.core.query import query
from praxis2.core.rmcp import Phase, get_phase, set_phase
from praxis2.core.seams import MinimalCompactor, PermissionDecision
from praxis2.core.state import State, TerminalReason
from praxis2.hooks.builtin import advance_phase_on_retrieve, doi_required, make_rmcp_stop_gate
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.permission import PhaseAwarePermission, RulePermissionPolicy
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import TURN_FINAL_TEXT, FakeLLMClient


class _RetrieveTool:
    name = "retrieve_cases"
    rmcp_op = "retrieve_cases"


class _ExecTool:
    name = "skill_runner"
    rmcp_op = "call_skill"


def _ok(tid="tu1"):
    return {"type": "tool_result", "tool_use_id": tid, "is_error": False,
            "content": "命中 3 条案例"}


def test_invariant1_execute_denied_until_retrieve_advances_phase():
    # §5④#1 闭环:retrieve 前 execute 被拒 → retrieve 成功推进相位 → execute 放行
    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    st = State()  # INIT
    assert pol.check(tool=_ExecTool(), payload={}, state=st).decision \
        is PermissionDecision.DENY  # 未 retrieve,拒
    # 检索工具成功 → PostToolUse hook 推进相位
    advance_phase_on_retrieve(_RetrieveTool(), {"id": "tu1"}, _ok(), st)
    assert get_phase(st) is Phase.RETRIEVE
    # 模拟 RMCP 流程推进到 EXECUTE(完整编排 M5)
    set_phase(st, Phase.EXECUTE)
    assert pol.check(tool=_ExecTool(), payload={}, state=st).decision \
        is PermissionDecision.ALLOW  # retrieve 已完成,放行


def test_advance_phase_on_retrieve_idempotent_and_only_on_success():
    st = State()
    advance_phase_on_retrieve(_RetrieveTool(), {"id": "t"}, _ok(), st)
    advance_phase_on_retrieve(_RetrieveTool(), {"id": "t"}, _ok(), st)  # 再来一次幂等
    assert get_phase(st) is Phase.RETRIEVE
    # 失败结果不推进相位
    st2 = State()
    err = {"type": "tool_result", "tool_use_id": "t", "is_error": True,
           "content": "检索失败"}
    advance_phase_on_retrieve(_RetrieveTool(), {"id": "t"}, err, st2)
    assert get_phase(st2) is Phase.INIT


def test_non_retrieve_tool_does_not_advance_phase():
    st = State()

    class _U:
        name = "read"
        rmcp_op = None

    advance_phase_on_retrieve(_U(), {"id": "t"}, _ok(), st)
    assert get_phase(st) is Phase.INIT


class WriteCase(Tool):
    name = "write_case"
    rmcp_op = "write_case"

    def input_schema(self):
        return {"type": "object", "properties": {}}

    async def run(self, payload):
        return ToolResult(ok=True, value="案例正文,无 doi")  # 触发 doi_required 否决


def _settings3():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


async def test_inv2_doi_veto_through_real_runner_post_hooks():
    # §5④#2 整合:DOI hook 经 SerialToolRunner.post_hooks 真否决并回喂满足条件
    reg = ToolRegistry()
    reg.register(WriteCase())
    runner = SerialToolRunner(reg, recovery_budget=3, post_hooks=[doi_required])
    st = State()
    # set_phase 仅语义标注(write_case 属 SEAL 白名单);本测试 runner 用默认
    # AllowAllPermission,相位门不参与此链路——专验 post_hook 否决层
    # (§5④#2 否决纯净性不依赖相位;相位门由 test_invariant1/T8 锁)
    set_phase(st, Phase.SEAL)
    results = await runner.run_turn(
        [{"id": "tu1", "name": "write_case", "input": {}}], st
    )
    assert results[0]["is_error"] is True
    assert "DOI" in results[0]["content"] and "满足条件" in results[0]["content"]


async def test_inv3_stop_gate_vetoes_final_through_query():
    # §5④#3 整合:证据链不完整 → query() Stop gate 否决终答、强制再走一轮
    # B.4(reviewer M1 C2):每终答都跑 hook → 用 wrapper 模拟"中间轮补足 ctx"使第二终答放行
    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3)
    # 两轮终答
    client = FakeLLMClient(turns=[TURN_FINAL_TEXT, TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "给结论"}]

    real_gate = make_rmcp_stop_gate()

    def gate_with_recovery(state):
        dec = real_gate(state)
        if dec.veto:
            state.tool_use_context["evidence_ok"] = True
            state.tool_use_context["anti_filter_ok"] = True
        return dec

    last = None
    async for e in query(
        st, client=client, registry=reg, settings=_settings3(),
        runner=runner, compactor=MinimalCompactor(),
        stop_hook=gate_with_recovery,
    ):
        last = e
    assert last == {"type": "end", "reason": TerminalReason.STOP.value}
    # FakeLLMClient 消耗了 2 个 turns(等价于原来 respx.calls.call_count == 2)
    assert client._idx == 2  # 显式锁"强制再走一轮":两轮 API
    assert sum(
        1 for m in st.messages
        if m["role"] == "user" and "RMCP 终态否决" in str(m["content"])
    ) == 1  # 否决一次、强制再走一轮后放行
    await client.aclose()

"""RMCP 相位单一真源(总纲 §8 S7,M3 关键前置)。

v1 已验证语义忠实抄录,不引入新相位/边/操作(D3:重新表达不改语义)。
真源:v1 praxis_kernel/phase.py:33-64 + _ALLOWED_OPS;
依据文档 AGENT-FRAMEWORK-2026-05-18.md §3(v1 phase.py 忠实抽取)。
Permission 层(tools/permission.py)与 hooks 层共同 import 本模块,唯一相位真源。"""

from enum import StrEnum  # ruff UP042 + py311

from praxis2.core.state import State


class Phase(StrEnum):
    INIT = "init"
    RETRIEVE = "retrieve"
    ANTI_FILTER = "anti_filter"
    PLAN = "plan"
    EXECUTE = "execute"
    SEAL = "seal"
    DONE = "done"


# v1 phase.py:43-64 转移表(线性主链 + 三处可回退 RETRIEVE)
TRANSITIONS: dict[Phase, frozenset[Phase]] = {
    Phase.INIT: frozenset({Phase.RETRIEVE}),
    Phase.RETRIEVE: frozenset({Phase.ANTI_FILTER}),
    Phase.ANTI_FILTER: frozenset({Phase.PLAN, Phase.RETRIEVE}),
    Phase.PLAN: frozenset({Phase.EXECUTE, Phase.RETRIEVE}),
    Phase.EXECUTE: frozenset({Phase.SEAL, Phase.PLAN, Phase.RETRIEVE}),
    Phase.SEAL: frozenset({Phase.DONE}),
    Phase.DONE: frozenset(),
}

# v1 _ALLOWED_OPS 每相位操作白名单(相位外操作 check_op 抛 PhaseError)
ALLOWED_OPS: dict[Phase, frozenset[str]] = {
    Phase.INIT: frozenset(),
    Phase.RETRIEVE: frozenset(
        {"retrieve_cases", "retrieve_rules", "retrieve_skills", "retrieve_neg_cases"}
    ),
    Phase.ANTI_FILTER: frozenset({"anti_retrieval"}),
    Phase.PLAN: frozenset({"plan_pipeline", "list_excluded_methods", "state_evidence"}),
    Phase.EXECUTE: frozenset({"call_skill"}),
    Phase.SEAL: frozenset(
        {"write_case", "write_neg_case", "promote_rule", "demote_rule"}
    ),
    Phase.DONE: frozenset(),
}


class PhaseError(Exception):
    """非法相位跃迁 / 相位外操作(v1 PhaseError 等价语义)。"""


class PhaseMachine:
    """v1 PhaseMachine 重新表达:advance(to) 非法跃迁抛 PhaseError;
    check_op(op) 相位外操作抛 PhaseError。代码层强制,非模型自律。"""

    def __init__(self, phase: Phase = Phase.INIT) -> None:
        self.phase = phase

    def advance(self, to: Phase) -> None:
        if to not in TRANSITIONS[self.phase]:
            raise PhaseError(f"非法相位跃迁:{self.phase.value} → {to.value}")
        self.phase = to

    def check_op(self, op: str) -> None:
        if op not in ALLOWED_OPS[self.phase]:
            raise PhaseError(
                f"操作 {op!r} 不在相位 {self.phase.value} 白名单"
                f"(需先跃迁到允许该操作的相位)"
            )


# 公开契约:M4 memory/session.py resume/持久化须 import 本常量(勿硬编码字符串)
PHASE_KEY = "rmcp_phase"


def get_phase(state: State) -> Phase:
    """读相位;未设过默认 INIT(绝不静默假设已完成 retrieve,§7.3.7)。"""
    return Phase(state.tool_use_context.get(PHASE_KEY, Phase.INIT.value))


def set_phase(state: State, phase: Phase) -> None:
    """直接置相位(resume 重建用;常规跃迁走 advance_phase)。
    tool_use_context[PHASE_KEY] 仅由本函数写入;外部勿直接改该 key
    (get_phase 对非法值会抛内建 ValueError 而非 PhaseError,排查成本高)。"""
    state.tool_use_context[PHASE_KEY] = phase.value


def advance_phase(state: State, to: Phase) -> None:
    """按 TRANSITIONS 跃迁;非法抛 PhaseError。M3 内存态,
    M4 memory/session.py 据 tool_use_context 持久化 + resume(§7.4.6)。"""
    m = PhaseMachine(get_phase(state))
    m.advance(to)
    set_phase(state, m.phase)

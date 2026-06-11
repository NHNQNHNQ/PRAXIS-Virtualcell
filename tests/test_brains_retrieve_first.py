from praxis2.agents.loader import resolve_agent
from praxis2.brains.migrate import build_fixture_brain
from praxis2.brains.retrieve_first import retrieve_first
from praxis2.core.prompt import Section
from praxis2.core.rmcp import Phase, get_phase, set_phase
from praxis2.core.seams import PermissionDecision
from praxis2.core.state import State
from praxis2.tools.permission import PhaseAwarePermission, RulePermissionPolicy


class _ExecTool:
    name = "skill_runner"
    rmcp_op = "call_skill"


def test_retrieve_hit_advances_phase_to_retrieve():
    st = State()  # INIT
    sel = resolve_agent("Cryo", user_query="冷冻电镜 三维重构")
    docs = build_fixture_brain("Cryo")
    res = retrieve_first(st, sel, domain_docs=docs,
                         common_docs=build_fixture_brain("_common"),
                         user_query="冷冻电镜 三维重构怎么做")
    assert get_phase(st) is Phase.RETRIEVE          # 检索成功推进相位
    assert res.degraded_to_bare is False
    assert all(isinstance(s, Section) for s in res.sections)


def test_retrieve_empty_does_not_advance_phase_execute_still_denied():
    st = State()
    sel = resolve_agent("Cryo", user_query="x")
    res = retrieve_first(st, sel, domain_docs=build_fixture_brain("Cryo"),
                         common_docs=build_fixture_brain("_common"),
                         user_query="完全无关的烹饪食谱")
    assert res.degraded_to_bare is True
    assert get_phase(st) is Phase.INIT              # 未推进(科学严谨不失守)
    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    d = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert d.decision is PermissionDecision.DENY    # execute 仍被拒


def test_end_to_end_retrieve_then_execute_allowed():
    # §5④#1 在 M5 大脑检索接入后仍成立:retrieve→(anti_filter→plan)→execute
    st = State()
    sel = resolve_agent("Enzyme", user_query="酶 催化 动力学")
    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    assert pol.check(tool=_ExecTool(), payload={}, state=st).decision \
        is PermissionDecision.DENY  # retrieve 前:拒
    retrieve_first(st, sel, domain_docs=build_fixture_brain("Enzyme"),
                   common_docs=build_fixture_brain("_common"),
                   user_query="酶 催化 米氏 动力学")
    assert get_phase(st) is Phase.RETRIEVE
    # 完整相位编排沿用 M3 体例(显式模拟 anti_filter→plan→execute)
    set_phase(st, Phase.ANTI_FILTER)
    set_phase(st, Phase.PLAN)
    set_phase(st, Phase.EXECUTE)
    assert pol.check(tool=_ExecTool(), payload={}, state=st).decision \
        is PermissionDecision.ALLOW  # retrieve 已完成:放行


def test_idempotent_retrieve_first_does_not_double_advance():
    st = State()
    sel = resolve_agent("Cryo", user_query="冷冻电镜")
    docs = build_fixture_brain("Cryo")
    retrieve_first(st, sel, domain_docs=docs,
                   common_docs=build_fixture_brain("_common"),
                   user_query="冷冻电镜 三维重构")
    # 二次调用:已在 RETRIEVE,守 S7 无 RETRIEVE→RETRIEVE 边(不抛 PhaseError)
    retrieve_first(st, sel, domain_docs=docs,
                   common_docs=build_fixture_brain("_common"),
                   user_query="冷冻电镜 颗粒挑选")
    assert get_phase(st) is Phase.RETRIEVE

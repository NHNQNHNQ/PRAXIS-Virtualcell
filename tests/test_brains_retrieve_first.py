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
    sel = resolve_agent("Virtualcell", user_query="\u51b7\u51bb\u7535\u955c \u4e09\u7ef4\u91cd\u6784")
    docs = build_fixture_brain("Virtualcell")
    res = retrieve_first(
        st, sel, domain_docs=docs, common_docs=build_fixture_brain("_common"), user_query="Virtualcell \u9886\u57df"
    )
    assert get_phase(st) is Phase.RETRIEVE
    assert res.degraded_to_bare is False
    assert all(isinstance(s, Section) for s in res.sections)


def test_retrieve_empty_does_not_advance_phase_execute_still_denied():
    st = State()
    sel = resolve_agent("Virtualcell", user_query="x")
    res = retrieve_first(
        st,
        sel,
        domain_docs=build_fixture_brain("Virtualcell"),
        common_docs=build_fixture_brain("_common"),
        user_query="\u5b8c\u5168\u65e0\u5173\u7684\u70f9\u996a\u98df\u8c31",
    )
    assert res.degraded_to_bare is True
    assert get_phase(st) is Phase.INIT
    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    d = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert d.decision is PermissionDecision.DENY


def test_end_to_end_retrieve_then_execute_allowed():

    st = State()
    sel = resolve_agent("Virtualcell", user_query="\u9176 \u50ac\u5316 \u52a8\u529b\u5b66")
    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    assert pol.check(tool=_ExecTool(), payload={}, state=st).decision is PermissionDecision.DENY
    retrieve_first(
        st,
        sel,
        domain_docs=build_fixture_brain("Virtualcell"),
        common_docs=build_fixture_brain("_common"),
        user_query="Virtualcell \u9886\u57df",
    )
    assert get_phase(st) is Phase.RETRIEVE

    set_phase(st, Phase.ANTI_FILTER)
    set_phase(st, Phase.PLAN)
    set_phase(st, Phase.EXECUTE)
    assert pol.check(tool=_ExecTool(), payload={}, state=st).decision is PermissionDecision.ALLOW


def test_idempotent_retrieve_first_does_not_double_advance():
    st = State()
    sel = resolve_agent("Virtualcell", user_query="\u51b7\u51bb\u7535\u955c")
    docs = build_fixture_brain("Virtualcell")
    retrieve_first(
        st, sel, domain_docs=docs, common_docs=build_fixture_brain("_common"), user_query="Virtualcell \u9886\u57df"
    )

    retrieve_first(
        st,
        sel,
        domain_docs=docs,
        common_docs=build_fixture_brain("_common"),
        user_query="Virtualcell \u9886\u57df \u4e8c\u6b21",
    )
    assert get_phase(st) is Phase.RETRIEVE

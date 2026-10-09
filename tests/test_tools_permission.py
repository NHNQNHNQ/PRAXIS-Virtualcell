from praxis2.core.rmcp import Phase, set_phase
from praxis2.core.seams import PermissionDecision
from praxis2.core.state import State
from praxis2.tools.permission import (
    PermissionMode,
    PhaseAwarePermission,
    Rule,
    RuleAction,
    RulePermissionPolicy,
    RuleSource,
)


class _Tool:
    name = "bash"


def _rules(*rs):
    return RulePermissionPolicy(list(rs))


def test_permission_modes_are_five_v1_set():
    assert [m.value for m in PermissionMode] == ["default", "acceptEdits", "plan", "auto", "bypassPermissions"]


def test_explicit_deny_beats_allow():
    pol = _rules(
        Rule(RuleAction.ALLOW, "bash"),
        Rule(RuleAction.DENY, "bash"),
    )
    res = pol.check(tool=_Tool(), payload={}, state=State())
    assert res.decision is PermissionDecision.DENY


def test_ask_beats_allow_but_deny_beats_ask():
    assert (
        _rules(Rule(RuleAction.ALLOW, "bash"), Rule(RuleAction.ASK, "bash"))
        .check(tool=_Tool(), payload={}, state=State())
        .decision
        is PermissionDecision.ASK
    )
    assert (
        _rules(Rule(RuleAction.ASK, "bash"), Rule(RuleAction.DENY, "bash"))
        .check(tool=_Tool(), payload={}, state=State())
        .decision
        is PermissionDecision.DENY
    )


def test_no_match_defaults_allow():
    res = _rules(Rule(RuleAction.DENY, "python")).check(tool=_Tool(), payload={}, state=State())
    assert res.decision is PermissionDecision.ALLOW


def test_bypass_mode_skips_rules():
    pol = RulePermissionPolicy([Rule(RuleAction.DENY, "bash")], mode=PermissionMode.BYPASS_PERMISSIONS)
    res = pol.check(tool=_Tool(), payload={}, state=State())
    assert res.decision is PermissionDecision.ALLOW


class _ExecTool:
    name = "skill_runner"
    rmcp_op = "call_skill"


class _UtilTool:
    name = "read_file"
    rmcp_op = None


def test_execute_tool_denied_before_retrieve_completed():

    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    st = State()
    res = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert res.decision is PermissionDecision.DENY
    assert "retrieve" in res.reason and "call_skill" in res.reason


def test_execute_tool_allowed_after_phase_reaches_execute():
    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    st = State()
    set_phase(st, Phase.EXECUTE)
    res = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert res.decision is PermissionDecision.ALLOW


def test_utility_tool_unrestricted_by_phase():

    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    res = pol.check(tool=_UtilTool(), payload={}, state=State())
    assert res.decision is PermissionDecision.ALLOW


def test_rule_deny_still_wins_over_phase_allow():

    pol = PhaseAwarePermission(RulePermissionPolicy([Rule(RuleAction.DENY, "skill_runner")]))
    st = State()
    set_phase(st, Phase.EXECUTE)
    res = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert res.decision is PermissionDecision.DENY


def test_tool_base_default_rmcp_op_is_none():
    from praxis2.tools.base import Tool

    assert Tool.rmcp_op is None


class _NamedTool:
    def __init__(self, name: str) -> None:
        self.name = name


def test_user_allow_cannot_override_builtin_deny():

    pol = RulePermissionPolicy(
        [
            Rule(action=RuleAction.DENY, tool_prefix="bash:rm", source=RuleSource.BUILTIN),
            Rule(action=RuleAction.ALLOW, tool_prefix="bash:rm", source=RuleSource.USER),
        ]
    )
    res = pol.check(tool=_NamedTool("bash:rm -rf /"), payload={}, state=State())
    assert res.decision is PermissionDecision.DENY
    assert "builtin" in res.reason


def test_admin_deny_overrides_user_allow():

    pol = RulePermissionPolicy(
        [
            Rule(action=RuleAction.ALLOW, tool_prefix="net:fetch", source=RuleSource.USER),
            Rule(action=RuleAction.DENY, tool_prefix="net:fetch", source=RuleSource.ADMIN),
        ]
    )
    res = pol.check(tool=_NamedTool("net:fetch"), payload={}, state=State())
    assert res.decision is PermissionDecision.DENY


def test_builtin_ask_overrides_admin_allow():

    pol = RulePermissionPolicy(
        [
            Rule(action=RuleAction.ALLOW, tool_prefix="x", source=RuleSource.ADMIN),
            Rule(action=RuleAction.ASK, tool_prefix="x", source=RuleSource.BUILTIN),
        ]
    )
    res = pol.check(tool=_NamedTool("x"), payload={}, state=State())
    assert res.decision is PermissionDecision.ASK


def test_same_tier_falls_back_to_action_priority():

    pol = RulePermissionPolicy(
        [
            Rule(action=RuleAction.ALLOW, tool_prefix="x", source=RuleSource.USER),
            Rule(action=RuleAction.DENY, tool_prefix="x", source=RuleSource.USER),
        ]
    )
    res = pol.check(tool=_NamedTool("x"), payload={}, state=State())
    assert res.decision is PermissionDecision.DENY


def test_default_source_is_user():

    r = Rule(action=RuleAction.DENY, tool_prefix="x")
    assert r.source is RuleSource.USER


def test_no_match_still_allow_with_source_tiers():

    pol = RulePermissionPolicy(
        [
            Rule(action=RuleAction.DENY, tool_prefix="bash", source=RuleSource.BUILTIN),
        ]
    )
    res = pol.check(tool=_NamedTool("net"), payload={}, state=State())
    assert res.decision is PermissionDecision.ALLOW


def test_retrieve_first_permission_matrix():
    from praxis2.core.rmcp import Phase, set_phase
    from praxis2.core.seams import (
        PermissionDecision,
        PermissionPolicy,
        PermissionResult,
    )
    from praxis2.core.state import State
    from praxis2.tools.permission import RetrieveFirstPermission

    class _AllowBase(PermissionPolicy):
        def check(self, *, tool, payload, state):
            return PermissionResult(PermissionDecision.ALLOW)

    class _DenyBase(PermissionPolicy):
        def check(self, *, tool, payload, state):
            return PermissionResult(PermissionDecision.DENY, "base \u62d2")

    class _ExecTool:
        name = "SkillExec"
        rmcp_op = "call_skill"

    class _ReadTool:
        name = "BrainQuery"
        rmcp_op = None

    pol = RetrieveFirstPermission(_AllowBase())

    # 1) INIT + rmcp_op → DENY
    st = State()
    d = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert d.decision is PermissionDecision.DENY
    assert "Retrieval is required" in (d.reason or "")

    st2 = State()
    set_phase(st2, Phase.RETRIEVE)
    assert pol.check(tool=_ExecTool(), payload={}, state=st2).decision is PermissionDecision.ALLOW

    assert pol.check(tool=_ReadTool(), payload={}, state=State()).decision is PermissionDecision.ALLOW

    pol_deny = RetrieveFirstPermission(_DenyBase())
    dd = pol_deny.check(tool=_ReadTool(), payload={}, state=State())
    assert dd.decision is PermissionDecision.DENY and dd.reason == "base \u62d2"

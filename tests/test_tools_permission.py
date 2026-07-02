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
    assert [m.value for m in PermissionMode] == [
        "default", "acceptEdits", "plan", "auto", "bypassPermissions"
    ]


def test_explicit_deny_beats_allow():
    pol = _rules(
        Rule(RuleAction.ALLOW, "bash"),
        Rule(RuleAction.DENY, "bash"),
    )
    res = pol.check(tool=_Tool(), payload={}, state=State())
    assert res.decision is PermissionDecision.DENY  # 显式 deny 优先于 allow(§7.3.6)


def test_ask_beats_allow_but_deny_beats_ask():
    assert _rules(Rule(RuleAction.ALLOW, "bash"), Rule(RuleAction.ASK, "bash")).check(
        tool=_Tool(), payload={}, state=State()
    ).decision is PermissionDecision.ASK
    assert _rules(Rule(RuleAction.ASK, "bash"), Rule(RuleAction.DENY, "bash")).check(
        tool=_Tool(), payload={}, state=State()
    ).decision is PermissionDecision.DENY


def test_no_match_defaults_allow():
    res = _rules(Rule(RuleAction.DENY, "python")).check(
        tool=_Tool(), payload={}, state=State()
    )
    assert res.decision is PermissionDecision.ALLOW  # 无规则命中 → 放行


def test_bypass_mode_skips_rules():
    pol = RulePermissionPolicy(
        [Rule(RuleAction.DENY, "bash")], mode=PermissionMode.BYPASS_PERMISSIONS
    )
    res = pol.check(tool=_Tool(), payload={}, state=State())
    assert res.decision is PermissionDecision.ALLOW  # bypass 仅 CI,跳过规则


class _ExecTool:
    name = "skill_runner"
    rmcp_op = "call_skill"  # EXECUTE 类


class _UtilTool:
    name = "read_file"
    rmcp_op = None  # 工具类,不受相位约束


def test_execute_tool_denied_before_retrieve_completed():
    # §5④#1 / §7.3.7:相位未完成 retrieve → execute 类工具 deny
    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    st = State()  # 默认 INIT(未 retrieve)
    res = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert res.decision is PermissionDecision.DENY
    assert "retrieve" in res.reason and "call_skill" in res.reason  # 为何拒+需先做什么


def test_execute_tool_allowed_after_phase_reaches_execute():
    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    st = State()
    set_phase(st, Phase.EXECUTE)  # 已走到 EXECUTE
    res = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert res.decision is PermissionDecision.ALLOW


def test_utility_tool_unrestricted_by_phase():
    # rmcp_op=None 的工具类(检索/读取/解析)不受相位门约束
    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    res = pol.check(tool=_UtilTool(), payload={}, state=State())
    assert res.decision is PermissionDecision.ALLOW


def test_rule_deny_still_wins_over_phase_allow():
    # 规则层 deny 优先(§7.3.6),即使相位允许
    pol = PhaseAwarePermission(
        RulePermissionPolicy([Rule(RuleAction.DENY, "skill_runner")])
    )
    st = State()
    set_phase(st, Phase.EXECUTE)
    res = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert res.decision is PermissionDecision.DENY


def test_tool_base_default_rmcp_op_is_none():
    from praxis2.tools.base import Tool

    assert Tool.rmcp_op is None  # 默认工具类不受相位约束(M1 工具无需改)


# ----- §7.3.6 source tier 优先级:内置 > 管理员 > 用户(Phase A.7, reviewer M1 C3) -----


class _NamedTool:
    """复用:按名构造任意工具(避免每 case 都另起一个 class)。"""

    def __init__(self, name: str) -> None:
        self.name = name


def test_user_allow_cannot_override_builtin_deny():
    """§7.3.6:用户 ALLOW 不能盖内置 DENY(rm -rf 反面教材)。"""
    pol = RulePermissionPolicy([
        Rule(action=RuleAction.DENY, tool_prefix="bash:rm", source=RuleSource.BUILTIN),
        Rule(action=RuleAction.ALLOW, tool_prefix="bash:rm", source=RuleSource.USER),
    ])
    res = pol.check(tool=_NamedTool("bash:rm -rf /"), payload={}, state=State())
    assert res.decision is PermissionDecision.DENY
    assert "builtin" in res.reason


def test_admin_deny_overrides_user_allow():
    """管理员 DENY 盖用户 ALLOW(组织级策略)。"""
    pol = RulePermissionPolicy([
        Rule(action=RuleAction.ALLOW, tool_prefix="net:fetch", source=RuleSource.USER),
        Rule(action=RuleAction.DENY, tool_prefix="net:fetch", source=RuleSource.ADMIN),
    ])
    res = pol.check(tool=_NamedTool("net:fetch"), payload={}, state=State())
    assert res.decision is PermissionDecision.DENY


def test_builtin_ask_overrides_admin_allow():
    """内置 ASK 盖管理员 ALLOW(更高 tier 内的判定生效,即便动作较宽)。"""
    pol = RulePermissionPolicy([
        Rule(action=RuleAction.ALLOW, tool_prefix="x", source=RuleSource.ADMIN),
        Rule(action=RuleAction.ASK, tool_prefix="x", source=RuleSource.BUILTIN),
    ])
    res = pol.check(tool=_NamedTool("x"), payload={}, state=State())
    assert res.decision is PermissionDecision.ASK


def test_same_tier_falls_back_to_action_priority():
    """同 tier 内仍走 DENY > ASK > ALLOW。"""
    pol = RulePermissionPolicy([
        Rule(action=RuleAction.ALLOW, tool_prefix="x", source=RuleSource.USER),
        Rule(action=RuleAction.DENY, tool_prefix="x", source=RuleSource.USER),
    ])
    res = pol.check(tool=_NamedTool("x"), payload={}, state=State())
    assert res.decision is PermissionDecision.DENY


def test_default_source_is_user():
    """Rule 不传 source → USER,既有调用方零回归。"""
    r = Rule(action=RuleAction.DENY, tool_prefix="x")
    assert r.source is RuleSource.USER


def test_no_match_still_allow_with_source_tiers():
    """无规则命中 → ALLOW(source 改造不破基础放行)。"""
    pol = RulePermissionPolicy([
        Rule(action=RuleAction.DENY, tool_prefix="bash", source=RuleSource.BUILTIN),
    ])
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
            return PermissionResult(PermissionDecision.DENY, "base 拒")

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
    assert "检索先行" in (d.reason or "")

    # 2) 已检索(phase!=INIT)+ rmcp_op → ALLOW
    st2 = State()
    set_phase(st2, Phase.RETRIEVE)
    assert pol.check(tool=_ExecTool(), payload={}, state=st2).decision \
        is PermissionDecision.ALLOW

    # 3) rmcp_op=None → 透传 ALLOW(即便 INIT)
    assert pol.check(tool=_ReadTool(), payload={}, state=State()).decision \
        is PermissionDecision.ALLOW

    # 4) base 非 ALLOW(DENY/ASK)优先返回,不进相位判定
    pol_deny = RetrieveFirstPermission(_DenyBase())
    dd = pol_deny.check(tool=_ReadTool(), payload={}, state=State())
    assert dd.decision is PermissionDecision.DENY and dd.reason == "base 拒"

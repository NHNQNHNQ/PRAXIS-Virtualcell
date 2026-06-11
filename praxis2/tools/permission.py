"""Permission 模式 + 规则优先级(总纲 §7.3.5/§7.3.6)。
相位感知策略见 Task 4 PhaseAwarePermission。"""

from dataclasses import dataclass
from enum import StrEnum  # ruff UP042 + py311
from typing import Any

from praxis2.core.rmcp import ALLOWED_OPS, Phase, get_phase
from praxis2.core.seams import PermissionDecision, PermissionPolicy, PermissionResult
from praxis2.core.state import State


class PermissionMode(StrEnum):
    DEFAULT = "default"  # 每步确认(M3 内核态:default 不主动 ask,交规则)
    ACCEPT_EDITS = "acceptEdits"
    PLAN = "plan"  # 只规划不执行(= RMCP retrieve 阶段拒所有 execute 类)
    AUTO = "auto"
    BYPASS_PERMISSIONS = "bypassPermissions"  # 跳过,仅 CI


class RuleAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class RuleSource(StrEnum):
    """规则来源(§7.3.6):内置 > 管理员 > 用户。同 tier 内按 DENY>ASK>ALLOW 动作裁决。"""

    BUILTIN = "builtin"
    ADMIN = "admin"
    USER = "user"


@dataclass
class Rule:
    """规则形如 Allow/Deny/Ask(tool 名前缀)。phase 非 None 时为相位感知规则
    (§7.3.6:Allow(Bash(conda:*), phase=execute));M3 用工具名前缀匹配。
    tool_prefix="" 匹配所有工具(有意支持的 catch-all);精确匹配须令
    tool_prefix 等于完整工具名;glob/路径模式语义见 §7.3.8(M-later)。
    source 默认 USER,显式标 admin/builtin 提优先级(§7.3.6)。"""

    action: RuleAction
    tool_prefix: str
    phase: str | None = None
    source: RuleSource = RuleSource.USER


# 动作优先级(同 tier 内):DENY > ASK > ALLOW
_PRIORITY = {RuleAction.DENY: 3, RuleAction.ASK: 2, RuleAction.ALLOW: 1}
# source tier 优先级:BUILTIN > ADMIN > USER(§7.3.6)
_SOURCE_PRIORITY = {RuleSource.BUILTIN: 3, RuleSource.ADMIN: 2, RuleSource.USER: 1}
_ACTION_TO_DECISION = {
    RuleAction.DENY: PermissionDecision.DENY,
    RuleAction.ASK: PermissionDecision.ASK,
    RuleAction.ALLOW: PermissionDecision.ALLOW,
}


class RulePermissionPolicy(PermissionPolicy):
    """规则匹配 + 两阶段优先级裁决(§7.3.6):
    1) 取最高 source tier(BUILTIN > ADMIN > USER);
    2) 该 tier 内按 DENY > ASK > ALLOW 选 winner。
    用户 ALLOW 不能盖内置 DENY;管理员 DENY 盖用户 ALLOW。
    无规则命中 → 放行(ALLOW)。bypassPermissions 模式跳过规则全放行(仅 CI)。
    同 tier 同 action 多规则命中:取规则列表首个(确定性,非防火墙 last-match)。
    ACCEPT_EDITS/PLAN/AUTO 三模式 M3 语义未接、行为同 DEFAULT;相位门语义由
    T4 PhaseAwarePermission 组合层实现,**勿在本类加相位分支**(责越界)。"""

    def __init__(
        self, rules: list[Rule], *, mode: PermissionMode = PermissionMode.DEFAULT
    ) -> None:
        self._rules = rules
        self._mode = mode

    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        if self._mode is PermissionMode.BYPASS_PERMISSIONS:
            return PermissionResult(PermissionDecision.ALLOW)
        name = getattr(tool, "name", "")
        matched = [r for r in self._rules if name.startswith(r.tool_prefix)]
        if not matched:
            return PermissionResult(PermissionDecision.ALLOW)
        # 阶段 1:取最高 source tier(builtin > admin > user)
        top_src_pri = max(_SOURCE_PRIORITY[r.source] for r in matched)
        in_tier = [r for r in matched if _SOURCE_PRIORITY[r.source] == top_src_pri]
        # 阶段 2:同 tier 内按动作优先级裁决(max 平局取首个,确定性)
        winner = max(in_tier, key=lambda r: _PRIORITY[r.action])
        dec = _ACTION_TO_DECISION[winner.action]
        reason = (
            None
            if dec is PermissionDecision.ALLOW
            else f"规则 {winner.source.value}/{winner.action.value} 命中工具 {name!r}"
        )
        return PermissionResult(dec, reason)


class PhaseAwarePermission(PermissionPolicy):
    """§7.3.7 RMCP 接入点:先过规则层(deny/ask 优先),规则未拒再过相位门。
    工具声明 rmcp_op(call_skill 等);该 op 不在当前相位 ALLOWED_OPS → deny,
    reason 含*为何拒* + *需先完成什么*,让模型自己补 retrieve(不停下问人,§4)。
    rmcp_op=None 的工具类(检索/读取/解析)不受相位约束。"""

    def __init__(self, rules: RulePermissionPolicy) -> None:
        self._rules = rules

    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        base = self._rules.check(tool=tool, payload=payload, state=state)
        if base.decision is not PermissionDecision.ALLOW:
            return base  # 规则层 deny/ask 优先(§7.3.6)
        op = getattr(tool, "rmcp_op", None)
        if op is None:
            return base  # 工具类,不受相位门约束
        phase = get_phase(state)
        if op in ALLOWED_OPS[phase]:
            return PermissionResult(PermissionDecision.ALLOW)
        # 依赖 v1 数据不变量:每个 op 唯一归属一个相位(无跨相位重复);
        # 若 M5 让某 op 入多相位白名单,此处取 ALLOWED_OPS 插入序首个
        need = next(
            (p.value for p, ops in ALLOWED_OPS.items() if op in ops), "(未知相位)"
        )
        return PermissionResult(
            PermissionDecision.DENY,
            f"当前相位 {phase.value} 不允许操作 {op!r}:RMCP 须检索先行,"
            f"请先完成 retrieve 等前置并跃迁到 {need} 相位(自行补检索,勿停下问人)",
        )


class RetrieveFirstPermission(PermissionPolicy):
    """§7.3.7 chat 生产证据门(检索先行):先过 base(deny/ask 优先);base 放行后,
    rmcp_op != None 的执行/写入类工具仅当本会话已发生成功检索(相位已离开 INIT)才放行,
    否则 DENY 并在 reason 引导模型自补 BrainQuery(不停下问人,§4)。rmcp_op=None 的
    检索/读/编排类工具透传。空/fixture/降级检索不推进相位 → 执行仍被拒(反幻觉不失守)。"""

    def __init__(self, base: PermissionPolicy) -> None:
        self._base = base

    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        base = self._base.check(tool=tool, payload=payload, state=state)
        if base.decision is not PermissionDecision.ALLOW:
            return base  # base 层 deny/ask 优先
        op = getattr(tool, "rmcp_op", None)
        if op is None:
            return base  # 检索/读/编排类,不受证据门约束
        if get_phase(state) is Phase.INIT:
            return PermissionResult(
                PermissionDecision.DENY,
                "检索先行:本会话尚无成功的大脑检索(BrainQuery 命中),不能执行/写入。"
                "请先用 BrainQuery 检索相关 cases/rules,命中后再调用"
                "(自行补检索,勿停下问人)。",
            )
        return PermissionResult(PermissionDecision.ALLOW)

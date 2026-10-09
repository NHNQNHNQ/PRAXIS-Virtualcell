from dataclasses import dataclass
from enum import StrEnum  # ruff UP042 + py311
from typing import Any

from praxis2.core.rmcp import ALLOWED_OPS, Phase, get_phase
from praxis2.core.seams import PermissionDecision, PermissionPolicy, PermissionResult
from praxis2.core.state import State


class PermissionMode(StrEnum):
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    PLAN = "plan"
    AUTO = "auto"
    BYPASS_PERMISSIONS = "bypassPermissions"


class RuleAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class RuleSource(StrEnum):
    BUILTIN = "builtin"
    ADMIN = "admin"
    USER = "user"


@dataclass
class Rule:
    action: RuleAction
    tool_prefix: str
    phase: str | None = None
    source: RuleSource = RuleSource.USER


_PRIORITY = {RuleAction.DENY: 3, RuleAction.ASK: 2, RuleAction.ALLOW: 1}

_SOURCE_PRIORITY = {RuleSource.BUILTIN: 3, RuleSource.ADMIN: 2, RuleSource.USER: 1}
_ACTION_TO_DECISION = {
    RuleAction.DENY: PermissionDecision.DENY,
    RuleAction.ASK: PermissionDecision.ASK,
    RuleAction.ALLOW: PermissionDecision.ALLOW,
}


class RulePermissionPolicy(PermissionPolicy):
    def __init__(self, rules: list[Rule], *, mode: PermissionMode = PermissionMode.DEFAULT) -> None:
        self._rules = rules
        self._mode = mode

    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        if self._mode is PermissionMode.BYPASS_PERMISSIONS:
            return PermissionResult(PermissionDecision.ALLOW)
        name = getattr(tool, "name", "")
        matched = [r for r in self._rules if name.startswith(r.tool_prefix)]
        if not matched:
            return PermissionResult(PermissionDecision.ALLOW)

        top_src_pri = max(_SOURCE_PRIORITY[r.source] for r in matched)
        in_tier = [r for r in matched if _SOURCE_PRIORITY[r.source] == top_src_pri]

        winner = max(in_tier, key=lambda r: _PRIORITY[r.action])
        dec = _ACTION_TO_DECISION[winner.action]
        reason = (
            None
            if dec is PermissionDecision.ALLOW
            else f"Rule {winner.source.value}/{winner.action.value}matches tool {name!r}"
        )
        return PermissionResult(dec, reason)


class PhaseAwarePermission(PermissionPolicy):
    def __init__(self, rules: RulePermissionPolicy) -> None:
        self._rules = rules

    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        base = self._rules.check(tool=tool, payload=payload, state=state)
        if base.decision is not PermissionDecision.ALLOW:
            return base
        op = getattr(tool, "rmcp_op", None)
        if op is None:
            return base
        phase = get_phase(state)
        if op in ALLOWED_OPS[phase]:
            return PermissionResult(PermissionDecision.ALLOW)

        need = next((p.value for p, ops in ALLOWED_OPS.items() if op in ops), "(unknown phase)")
        return PermissionResult(
            PermissionDecision.DENY,
            (
                f"Current phase {phase.value} does not allow operation {op!r}: "
                "RMCP requires retrieve first. Complete prerequisites and "
                f"transition to {need} phase before proceeding"
            ),
        )


class RetrieveFirstPermission(PermissionPolicy):
    def __init__(self, base: PermissionPolicy) -> None:
        self._base = base

    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        base = self._base.check(tool=tool, payload=payload, state=state)
        if base.decision is not PermissionDecision.ALLOW:
            return base
        op = getattr(tool, "rmcp_op", None)
        if op is None:
            return base
        if get_phase(state) is Phase.INIT:
            return PermissionResult(
                PermissionDecision.DENY,
                (
                    "Retrieval is required before execution or writin"
                    "g. First use BrainQuery to retrieve a relevant c"
                    "ase or rule, then retry."
                ),
            )
        return PermissionResult(PermissionDecision.ALLOW)

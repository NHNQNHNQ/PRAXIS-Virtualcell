"""Check ModulePlan internal consistency without mutation. Entry verdicts cannot be more optimistic than routing;
mismatches cannot accept; nonreject engines must belong to the module; overall verdict must be the most
conservative entry. Evidence-level mapping is a separate check.
"""
from __future__ import annotations

from praxis_virtualcell.biological_modules import modules as M

_SEVERITY = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3, "reject": 3}


def _sev(v: str) -> int:
    return _SEVERITY.get(v, 3)


def check_module_plan(plan: dict) -> list[str]:
    """Return consistency violations for a ModulePlan dictionary; an empty list means no violations."""
    violations: list[str] = []
    entries = plan.get("entries", [])
    for e in entries:
        mid = e.get("module")

        if _sev(e.get("verdict")) < _sev(e.get("route_disposition")):
            violations.append(
                f"verdict_more_optimistic_than_route[{mid}]: "
                f"verdict={e.get('verdict')} < route={e.get('route_disposition')}")

        if e.get("mismatch") and e.get("verdict") == "accept":
            violations.append(f"mismatch_entry_accepted[{mid}]: mismatch={e.get('mismatch')} but verdict is accept")

        if mid in M.MODULES:
            legal = M.MODULES[mid]["engines"]
            eng = e.get("engine")
            if legal and eng not in legal and eng != "reject":
                violations.append(
                    f"engine_out_of_whitelist[{mid}]: {eng} ∉ {legal}")

    if entries:
        most_conservative = max(_sev(e.get("verdict")) for e in entries)
        if _sev(plan.get("overall_verdict")) < most_conservative:
            violations.append(
                f"overall_more_optimistic: overall={plan.get('overall_verdict')} "
                f"is more optimistic than the most conservative entry (severity={most_conservative})")
    return violations

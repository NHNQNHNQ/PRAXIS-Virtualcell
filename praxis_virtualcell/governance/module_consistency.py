"""cross-module consistency 校验(G4 铺路)。纯函数,验 ModulePlan(dict 或 ModulePlan.to_dict())
内部一致性,返回违规字符串列表(空 = 一致)。

规则(全 fail-closed 方向):
1. verdict 不得比 route_disposition 更乐观(更乐观 = severity 更低)。
2. mismatch 非 None → verdict 不得 accept。
3. engine 不在 MODULES[mid].engines 白名单(且非 reject)→ 违规。
4. overall_verdict 必须 = 各 entry verdict 最保守(不得比最保守 entry 更乐观)。

evidence level(E0–E5)不在此校验(留 Phase 4/5;那时管线带 reliability/OOD 信号)。
本校验器供 Critic 未来 G4 复用 + Phase 3 独立测试;不改现有 Critic。
"""
from __future__ import annotations

from praxis_virtualcell.biological_modules import modules as M

_SEVERITY = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3, "reject": 3}


def _sev(v: str) -> int:
    return _SEVERITY.get(v, 3)   # 未知 → 最保守


def check_module_plan(plan: dict) -> list[str]:
    """返回违规说明列表(空 = 无违规)。plan = ModulePlan.to_dict()。"""
    violations: list[str] = []
    entries = plan.get("entries", [])
    for e in entries:
        mid = e.get("module")
        # 1) verdict 不得比 route 更乐观
        if _sev(e.get("verdict")) < _sev(e.get("route_disposition")):
            violations.append(
                f"verdict_more_optimistic_than_route[{mid}]: "
                f"verdict={e.get('verdict')} < route={e.get('route_disposition')}")
        # 2) mismatch 命中不得 accept
        if e.get("mismatch") and e.get("verdict") == "accept":
            violations.append(f"mismatch_entry_accepted[{mid}]: mismatch={e.get('mismatch')} 却 accept")
        # 3) engine 白名单
        if mid in M.MODULES:
            legal = M.MODULES[mid]["engines"]
            eng = e.get("engine")
            if legal and eng not in legal and eng != "reject":
                violations.append(
                    f"engine_out_of_whitelist[{mid}]: {eng} ∉ {legal}")
    # 4) overall 不得比最保守 entry 更乐观
    if entries:
        most_conservative = max(_sev(e.get("verdict")) for e in entries)
        if _sev(plan.get("overall_verdict")) < most_conservative:
            violations.append(
                f"overall_more_optimistic: overall={plan.get('overall_verdict')} "
                f"比最保守 entry(sev={most_conservative})更乐观")
    return violations

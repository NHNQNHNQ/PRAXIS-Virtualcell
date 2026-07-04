"""safety_contract:LLM 编排的"只能从候选选"约束内核(纯函数,零 LLM/bus 依赖)。

复刻 LLMRouter(agents_llm/llm_router.py)的 `[a for a in ... if a in candidates]`:
LLM 出的 module 集必须过滤成 candidate 子集;candidate 全集 = Phase 3 确定性 primary/secondary
∪ 该物种非 unsupported 的模块。fail-closed:LLM 失败/越界 → 回退确定性,不丢 primary、不给
unsupported module 硬解释。
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.biological_modules import modules as M


def build_candidate_modules(req: dict, module_support: dict) -> list[str]:
    """candidate 全集:确定性 primary/secondary ∪ 该物种非 unsupported 模块。
    按 MODULE_ORDER 排序、去重。fail-closed:primary 一定在内(即使 support 标 unsupported)。"""
    primary = module_rules.pick_primary(req)
    secondary = module_rules.pick_secondary(req, primary)
    supported = {mid for mid in M.MODULE_ORDER
                 if (module_support.get(mid) or {}).get("support") != "unsupported"}
    cand = ({primary} | set(secondary) | supported)
    cand.add(primary)                          # primary 保底(即使被标 unsupported 也不丢主模块)
    return sorted(cand, key=M.MODULE_ORDER.index)


def filter_to_supported_modules(llm_modules: list, candidates: list[str]) -> list[str]:
    """复刻 LLMRouter 过滤:只保留 ∈ candidates 的 module,去重,按 candidates 序。"""
    cand_set = set(candidates)
    llm_set = set(llm_modules or [])
    out: list[str] = []
    for c in candidates:                       # 按 candidates 顺序输出
        if c in llm_set and c in cand_set and c not in out:
            out.append(c)
    return out


def sanitize_llm_plan(raw_content: str | None, candidates: list[str],
                      *, primary: str) -> dict:
    """解析 LLM JSON {selected_modules, reasoning_summary, risk_flags} → 合法结构(fail-closed)。
    content 空 → llm_unavailable;JSONDecodeError → llm_parse_failed;任一异常路径 selected 保底含 primary。"""
    out = {"selected_modules": [], "reasoning_summary": "",
           "risk_flags": [], "candidates": list(candidates)}
    _fallback = [primary] if primary in candidates else list(candidates[:1])
    if not raw_content:
        out["risk_flags"] = ["llm_unavailable"]
        out["selected_modules"] = _fallback
        return out
    # 整段后处理纳入同一 try:
    # - json.loads 成功但非 object(list/int/str/bool/None)→ d.get 抛 AttributeError
    # - selected_modules 为非可迭代标量(如 123)→ filter 内 set(123) 抛 TypeError
    # 任一异常都走 fallback(含 primary),绝不崩溃、绝不丢主模块。
    try:
        d = json.loads(raw_content)
        sel = filter_to_supported_modules(d.get("selected_modules") or [], candidates)
        if primary in candidates and primary not in sel:
            sel = [primary] + sel              # primary 保底(LLM 不可删 primary)
        rf = d.get("risk_flags")
        out["selected_modules"] = sel
        out["reasoning_summary"] = str(d.get("reasoning_summary", ""))[:500]
        out["risk_flags"] = list(rf) if isinstance(rf, list) else []  # 只接受 list,否则丢弃(不把字符串逐字符拆)
    except (json.JSONDecodeError, TypeError, AttributeError):
        out["risk_flags"] = ["llm_parse_failed"]
        out["selected_modules"] = _fallback
    return out


def assert_plan_within_bounds(plan: dict, candidates: list[str]) -> list[str]:
    """核验 ModulePlan(dict)的 primary/secondary/entries module 全 ∈ candidates。越界 → 违规串列表。"""
    cand_set = set(candidates)
    violations: list[str] = []
    for mid in ([plan.get("primary")] + list(plan.get("secondary", []))
                + [e.get("module") for e in plan.get("entries", [])]):
        if mid is not None and mid not in cand_set:
            violations.append(f"module_out_of_candidates: {mid} ∉ {sorted(cand_set)}")
    return sorted(set(violations))

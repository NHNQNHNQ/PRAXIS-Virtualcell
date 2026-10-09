"""Pure candidate-only constraint for optional LLM orchestration. Candidates combine deterministic
primary/secondary modules with species-supported modules. Filter all LLM selections to this set;
invalid/unavailable output falls back without losing primary or inventing unsupported-module evidence.
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.biological_modules import modules as M


def build_candidate_modules(req: dict, module_support: dict) -> list[str]:
    """Return deterministic primary/secondary plus supported species modules, deduplicated in MODULE_ORDER. Primary
    remains included even when its support is unsupported.
    """
    primary = module_rules.pick_primary(req)
    secondary = module_rules.pick_secondary(req, primary)
    supported = {mid for mid in M.MODULE_ORDER
                 if (module_support.get(mid) or {}).get("support") != "unsupported"}
    cand = ({primary} | set(secondary) | supported)
    cand.add(primary)
    return sorted(cand, key=M.MODULE_ORDER.index)


def filter_to_supported_modules(llm_modules: list, candidates: list[str]) -> list[str]:
    """Keep only candidate modules, remove duplicates, and retain candidate order."""
    cand_set = set(candidates)
    llm_set = set(llm_modules or [])
    out: list[str] = []
    for c in candidates:
        if c in llm_set and c in cand_set and c not in out:
            out.append(c)
    return out


def sanitize_llm_plan(raw_content: str | None, candidates: list[str],
                      *, primary: str) -> dict:
    """Parse selected_modules/reasoning_summary/risk_flags JSON into a valid candidate subset. Empty content yields
    llm_unavailable; invalid JSON yields llm_parse_failed. Every failure path retains primary.
    """
    out = {"selected_modules": [], "reasoning_summary": "",
           "risk_flags": [], "candidates": list(candidates)}
    _fallback = [primary] if primary in candidates else list(candidates[:1])
    if not raw_content:
        out["risk_flags"] = ["llm_unavailable"]
        out["selected_modules"] = _fallback
        return out




    try:
        d = json.loads(raw_content)
        sel = filter_to_supported_modules(d.get("selected_modules") or [], candidates)
        if primary in candidates and primary not in sel:
            sel = [primary] + sel
        rf = d.get("risk_flags")
        out["selected_modules"] = sel
        out["reasoning_summary"] = str(d.get("reasoning_summary", ""))[:500]

        out["risk_flags"] = [f for f in rf if isinstance(f, str)] if isinstance(rf, list) else []


    except (json.JSONDecodeError, TypeError, AttributeError, RecursionError):
        out["risk_flags"] = ["llm_parse_failed"]
        out["selected_modules"] = _fallback
    return out


def assert_plan_within_bounds(plan: dict, candidates: list[str]) -> list[str]:
    """Check that primary/secondary/entry modules belong to candidates; return violations for out-of-bounds plans."""
    cand_set = set(candidates)
    violations: list[str] = []
    for mid in ([plan.get("primary")] + list(plan.get("secondary", []))
                + [e.get("module") for e in plan.get("entries", [])]):
        if mid is not None and mid not in cand_set:
            violations.append(f"module_out_of_candidates: {mid} ∉ {sorted(cand_set)}")
    return sorted(set(violations))

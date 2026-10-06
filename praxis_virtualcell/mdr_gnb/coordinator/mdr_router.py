"""GNB 维度声明式 presence-absence 四档路由(adapt 自 route_table.py 骨架)。

不跑模型,只查 PredictorRegistry 能力图 + 物种固有耐药先验,决定 disposition:
  accept    请求的 output_kind 有已注册专用模型(如 MIC 回归)
  caution   有模型但需特殊处理(固有耐药物种/机理请求但 G3 未过 → 降机制来源)
  downgrade 只有规则基线兜底(请求 MIC 却无 mic_scalar 模型 → 不假装,降为 SIR/规则)
  abstain   无任何适用能力(物种缺失/药类不在训练分布)

固有耐药物种(D6)一律打 intrinsic_resistance_species 标,进 breakpoint/rule 特殊处理。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from praxis_virtualcell.mdr_gnb.predictors.registry import PredictorRegistry, PredictorSpec

# 请求 output 关键词 → registry output_kind
_OUTPUT_MAP = {"MIC_range": "mic_scalar", "MIC": "mic_scalar",
               "SIR": "sir_class", "mechanism": "mechanism_state",
               "activity": "sm_activity",              # 线B:化合物结构→活性(QSAR)
               "peptide_activity": "peptide_activity"}  # 线B B5:肽序列→活性(QSAR)
# D6:固有耐药/折点极少物种,须特殊处理
_INTRINSIC = {"stenotrophomonas_maltophilia", "serratia_marcescens",
              "proteus_mirabilis", "morganella_morganii"}


def requested_output_kinds(req: dict[str, Any]) -> list[str]:
    """Map public requested outputs to the canonical runtime capability kinds.

    The cache-integrity preflight and the router must use this one mapping.  If
    they diverge, a cached response could be admitted for a different model set
    than the one the production router would inspect.
    """
    return [
        _OUTPUT_MAP[output]
        for output in req.get("requested_outputs", [])
        if output in _OUTPUT_MAP
    ]


@dataclass
class MDRRouteDecision:
    species: str
    drug: str
    disposition: str                       # accept/caution/downgrade/abstain
    reason: str
    candidates: list[PredictorSpec] = field(default_factory=list)
    unready_candidates: list[dict[str, str]] = field(default_factory=list)
    caution_flags: list[str] = field(default_factory=list)
    requested_kinds: list[str] = field(default_factory=list)


def route_mdr(req: dict, registry: PredictorRegistry) -> MDRRouteDecision:
    species = req.get("species", "") or ""
    drug = req.get("drug", "")
    drug_class = req.get("drug_class", "") or ""
    kinds = requested_output_kinds(req)
    flags: list[str] = []
    if species in _INTRINSIC:
        flags.append("intrinsic_resistance_species")

    if not species or not drug_class:
        return MDRRouteDecision(species, drug, "abstain",
                                "species_or_drug_class_missing",
                                caution_flags=flags, requested_kinds=kinds)

    # 汇总所有请求 kind 的候选
    cands: list[PredictorSpec] = []
    for k in kinds:
        cands.extend(registry.discover(species=species, drug_class=drug_class, output_kind=k))
    # 去重(按 name@version)
    seen, uniq = set(), []
    for s in cands:
        key = f"{s.name}@{s.version}"
        if key not in seen:
            seen.add(key); uniq.append(s)

    if not uniq:
        return MDRRouteDecision(species, drug, "abstain",
                                "no_registered_capability",
                                caution_flags=flags, requested_kinds=kinds)

    # 注册只表示 declared。真正进入生产候选的必须在此时通过精确 artifact/SHA/依赖/
    # schema probe；run_mdr_query 的 no_successful_predictor 仍是最后一道防线，不能代替路由门。
    readiness_ctx = {
        "species": species,
        "drug": drug,
        "drug_class": drug_class,
        "requested_outputs": list(req.get("requested_outputs", [])),
    }
    ready_specs: list[PredictorSpec] = []
    unready: list[dict[str, str]] = []
    for spec in uniq:
        ready, reason_code = spec.check_readiness(readiness_ctx)
        if ready:
            ready_specs.append(spec)
        else:
            unready.append({"name": spec.name, "reason_code": reason_code})

    if not ready_specs:
        return MDRRouteDecision(
            species,
            drug,
            "abstain",
            "no_ready_capability",
            candidates=[],
            unready_candidates=unready,
            caution_flags=flags,
            requested_kinds=kinds,
        )

    kinds_found = {s.output_kind for s in ready_specs}

    # 机理请求但 G3 未过(无 mechanism_state 候选) → caution 降机制来源
    if "mechanism_state" in kinds and "mechanism_state" not in kinds_found:
        flags.append("mechanism_g3_not_passed")

    # 请求了 MIC 但无 mic_scalar 模型 → downgrade(只有规则/SIR 兜底,不假装 MIC)
    if "mic_scalar" in kinds and "mic_scalar" not in kinds_found:
        return MDRRouteDecision(species, drug, "downgrade",
                                "mic_requested_but_only_rule_fallback",
                                candidates=ready_specs, unready_candidates=unready,
                                caution_flags=flags, requested_kinds=kinds)

    disposition = "caution" if flags else "accept"
    reason = ("special_handling_required" if flags else "specialized_model_available")
    return MDRRouteDecision(species, drug, disposition, reason,
                            candidates=ready_specs, unready_candidates=unready,
                            caution_flags=flags, requested_kinds=kinds)

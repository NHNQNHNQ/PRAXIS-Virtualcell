"""W5.1(v0.4,Phase II):微生物 培养基/碳源切换 → growth case(环境扰动)。

复用 E. coli GEM(e_coli_core),把默认葡萄糖最小培养基换成其它单一碳源(乙酸/琥珀酸/…),
FBA 算生长 → 证明 agent 能处理 **gene 以外的环境扰动**(medium 对象),并受治理产出。

治理:请求碳源不在模型 exchange → abstain(不虚构);部分不可得 → caution。

科学默认(写明依据):单一碳源上限 -10 mmol/gDW/h(cobra textbook 惯例),有氧(O2 开放);
参考态 = glucose 最小培养基(= WT)。
"""
from __future__ import annotations

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents.route_table import route

# 常见碳源名 → e_coli_core exchange 反应 id
CARBON_EXCHANGES = {
    "glucose": "EX_glc__D_e",
    "fructose": "EX_fru_e",
    "acetate": "EX_ac_e",
    "succinate": "EX_succ_e",
    "lactate": "EX_lac__D_e",
    "akg": "EX_akg_e",
    "alpha-ketoglutarate": "EX_akg_e",
    "pyruvate": "EX_pyr_e",
}
_GLUCOSE_EX = "EX_glc__D_e"
_UPTAKE_LB = -10.0

_BOUNDARY = ("FBA growth 是约束型最优通量的相对量(steady-state、单碳源上限 -10、有氧),**非**绝对"
             "生长速率;e_coli_core 是核心代谢子集,只覆盖常见碳源;碳源不在模型 exchange 即弃权,"
             "不代表该碳源不可利用,仅表'此重建无法评估'。")


def carbon_growth(gem, carbon_name: str, uptake_lb: float = _UPTAKE_LB) -> float | None:
    """把碳源换成 carbon_name,返回 FBA growth;碳源不在模型 → None。"""
    ex = CARBON_EXCHANGES.get(str(carbon_name).strip().lower())
    if ex is None or not gem.model.reactions.has_id(ex):
        return None
    with gem.model:
        if gem.model.reactions.has_id(_GLUCOSE_EX):
            gem.model.reactions.get_by_id(_GLUCOSE_EX).lower_bound = 0.0
        gem.model.reactions.get_by_id(ex).lower_bound = uptake_lb
        return max(float(gem.model.slim_optimize()), 0.0)


def run_medium_shift_case(raw_req: dict, gem=None):
    """微生物碳源切换 growth case → 7 部分 CaseReport(真实数值)。返回 (CaseReport, RouteDecision)。"""
    from praxis_virtualcell.predictors.mechanistic.ecoli_gem import EcoliGEM

    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "gem_fba":
        raise ValueError(f"medium-shift case 期望 gem_fba,route 给了 {dec.engine}")
    gem = gem or EcoliGEM()

    glucose_growth = carbon_growth(gem, "glucose") or gem.wt_growth
    rows, missing = [], []
    for c in norm["perturbation_targets"]:
        g = carbon_growth(gem, c)
        if g is None:
            missing.append(c)
            rows.append({"carbon": c, "in_model": False, "growth": None, "ratio_vs_glucose": None})
        else:
            rows.append({"carbon": c, "in_model": True, "growth": round(g, 5),
                         "ratio_vs_glucose": round(g / glucose_growth, 4) if glucose_growth else None})

    n_ok = sum(1 for r in rows if r["in_model"])
    if n_ok == 0:
        disposition, flags = "abstain", ["all_carbon_sources_not_in_model"]
    elif missing:
        disposition, flags = "caution", [f"carbon_not_in_model:{missing}"]
    else:
        disposition, flags = "accept", []

    report = CaseReport(
        case_id=raw_req.get("case_id", "S_ecoli_carbon_shift"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "normalized_targets": norm["perturbation_targets"],
                              "target_output": norm["target_output"]},
        models_tools_selected={"engine": dec.engine, "tool": "cobrapy e_coli_core (textbook)",
                               "method": "FBA 单碳源培养基切换", "reason": dec.reason},
        raw_output={"reference": "glucose minimal", "glucose_growth": round(glucose_growth, 5),
                    "carbon_sources": rows},
        baseline_comparison={"baseline": "glucose minimal growth", "glucose_growth": round(glucose_growth, 5),
                             "n_in_model": n_ok, "n_missing": len(missing)},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "cobrapy", "model": "e_coli_core (textbook)", "objective": "biomass FBA",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    )
    return report, dec

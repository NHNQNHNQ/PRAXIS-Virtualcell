"""R3(v0.5):Bacteria antibiotic → growth case —— 抗生素靶反应抑制的 FBA(填应用 2 例 2C)。

数据:iML1515(全基因组 E. coli GEM,BiGG,`data/gems/iML1515.xml.gz`)—— 含叶酸合成等抗生素靶反应
(e_coli_core 无)。抗生素建模为**靶代谢反应抑制**(knock_out)→ FBA growth。复用 `GemModel`。

治理:抗生素靶反应在模型 → 预测生长效应(accept);靶为**非代谢过程**(如喹诺酮→DNA 旋转酶、
β-内酰胺→细胞壁,不在代谢 GEM)或未知 → **abstain**(不虚构,机制模型不适用该靶)。不训练模型。
"""
from __future__ import annotations

from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.mechanistic.gem_model import GemModel

_IML1515 = Path(__file__).resolve().parents[3] / "data" / "gems" / "iML1515.xml.gz"

# 抗生素 → 靶代谢反应 id(iML1515);None = 靶非代谢过程(GEM 不适用 → abstain)
ANTIBIOTIC_TARGETS = {
    "trimethoprim": "DHFR",        # 二氢叶酸还原酶
    "sulfamethoxazole": "DHPS2",   # 二氢蝶酸合酶
    "sulfamethazine": "DHPS2",
    "ciprofloxacin": None,         # DNA 旋转酶(非代谢)→ abstain
    "ampicillin": None,            # 细胞壁合成(非代谢 GEM)→ abstain
}
_BOUNDARY = ("FBA growth 是约束型最优通量相对量(steady-state),**非**绝对生长/MIC;抗生素建模为靶代谢"
             "反应完全抑制(理想化);iML1515 覆盖代谢,**非代谢靶**(旋转酶/细胞壁)不适用 → 弃权;"
             "in-silico,需湿实验证实。")

_gem_cache = {}


def _gem() -> GemModel:
    if "iml" not in _gem_cache:
        _gem_cache["iml"] = GemModel(str(_IML1515))
    return _gem_cache["iml"]


def run_antibiotic_case(raw_req: dict, gem: GemModel | None = None):
    """Bacteria antibiotic → growth case → 7 部分 CaseReport(真实靶抑制 FBA + 受治理裁决)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "gem_fba":
        raise ValueError(f"antibiotic case 期望 gem_fba,route 给了 {dec.engine}")
    gem = gem or _gem()

    results, dispositions, flags = [], [], []
    for ab in norm["perturbation_targets"]:
        key = ab.lower()
        if key not in ANTIBIOTIC_TARGETS:
            results.append({"antibiotic": ab, "target_rxn": None, "known": False})
            dispositions.append("abstain")
            flags.append(f"unknown_antibiotic:{ab}")
            continue
        rxn = ANTIBIOTIC_TARGETS[key]
        if rxn is None:
            results.append({"antibiotic": ab, "target_rxn": "non-metabolic", "known": True, "in_model": False})
            dispositions.append("abstain")
            flags.append(f"non_metabolic_target:{ab}")
            continue
        if not gem.model.reactions.has_id(rxn):
            results.append({"antibiotic": ab, "target_rxn": rxn, "in_model": False})
            dispositions.append("abstain")
            flags.append(f"target_rxn_not_in_model:{rxn}")
            continue
        with gem.model:
            gem.model.reactions.get_by_id(rxn).knock_out()
            g = max(float(gem.model.slim_optimize()), 0.0)
        ratio = g / gem.wt_growth if gem.wt_growth else 0.0
        results.append({"antibiotic": ab, "target_rxn": rxn, "in_model": True,
                        "growth": round(g, 5), "ratio_vs_wt": round(ratio, 4),
                        "growth_arrest": g < 1e-6})
        dispositions.append("accept")

    order = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3}
    disposition = max(dispositions, key=lambda x: order[x]) if dispositions else "abstain"

    return CaseReport(
        case_id=raw_req.get("case_id", "S_ecoli_antibiotic"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "normalized_targets": norm["perturbation_targets"], "target_output": norm["target_output"]},
        models_tools_selected={"engine": dec.engine, "tool": "cobrapy iML1515 (全基因组 E. coli)",
                               "method": "抗生素靶代谢反应抑制 FBA", "reason": dec.reason},
        raw_output={"wt_growth": round(gem.wt_growth, 5), "antibiotics": results},
        baseline_comparison={"baseline": "WT (无抗生素) growth", "wt_growth": round(gem.wt_growth, 5),
                             "n_growth_arrest": sum(1 for r in results if r.get("growth_arrest"))},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "cobrapy", "model": "iML1515", "objective": "biomass FBA",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    ), dec

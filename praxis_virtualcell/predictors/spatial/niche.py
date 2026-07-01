"""R5(v0.5):Spatial niche 依赖状态 case —— 空间微环境对肿瘤细胞 EMT 状态的影响(填应用 5 例 5B)。

数据:squidpy `imc`(乳腺癌 Imaging Mass Cytometry)的 committed 子集
(`data/cellstate/imc_niche_subset.json`,肿瘤细胞 × 空间 niche + Vimentin/ECadherin)。niche 由**空间
k-NN 邻域的间质细胞占比**在建子集时预计算(stroma_adjacent / stroma_poor / intermediate)。

分析:EMT niche score = Vimentin − ECadherin;比较间质邻接 vs 间质贫瘠 niche 的肿瘤细胞(Cohen's d)。
可检验生物学:间质邻接肿瘤细胞更间质性(部分 EMT,间质诱导)。治理:niche 差异强→accept,中等→caution,
弱→downgrade;niche 细胞不足→abstain。不训练模型。
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.state.scoring import cohens_d

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "cellstate" / "imc_niche_subset.json"
_D_ACCEPT, _D_CAUTION = 0.8, 0.3
_BOUNDARY = ("EMT niche score = Vimentin − ECadherin(IMC 蛋白表达,arcsinh),**非**绝对 EMT 程度;"
             "niche 由空间 k-NN 邻域间质占比定义;imc 单样本乳腺癌;downgrade/caution 表 niche 效应弱/中等;"
             "间质邻接肿瘤更间质性是可检验锚点(间质诱导 EMT)。")


class SpatialNicheDB:
    """imc niche 子集(committed):肿瘤细胞 × niche + Vimentin/ECadherin。"""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))

    def emt_by_niche(self, niche_a: str = "stroma_adjacent", niche_b: str = "stroma_poor") -> dict:
        a, b = [], []
        for c in self._d["cells"]:
            score = c["vimentin"] - c["ecadherin"]
            if c["niche"] == niche_a:
                a.append(score)
            elif c["niche"] == niche_b:
                b.append(score)
        return {"niche_a": niche_a, "niche_b": niche_b, "n_a": len(a), "n_b": len(b),
                "mean_a": round(sum(a) / len(a), 3) if a else None,
                "mean_b": round(sum(b) / len(b), 3) if b else None,
                "cohens_d": round(cohens_d(a, b), 3)}


def run_spatial_niche_case(raw_req: dict, db: SpatialNicheDB | None = None):
    """Spatial niche 依赖状态 case → 7 部分 CaseReport(真实 niche 差异 + 受治理裁决)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "spatial_niche":
        raise ValueError(f"spatial niche case 期望 spatial_niche,route 给了 {dec.engine}")
    db = db or SpatialNicheDB()

    res = db.emt_by_niche()
    d = abs(res["cohens_d"])
    if res["n_a"] < 2 or res["n_b"] < 2:
        disposition, flags = "abstain", ["insufficient_niche_cells"]
    elif d >= _D_ACCEPT:
        disposition, flags = "accept", []
    elif d >= _D_CAUTION:
        disposition, flags = "caution", [f"moderate_niche_effect:d={res['cohens_d']}"]
    else:
        disposition, flags = "downgrade", [f"weak_niche_effect:d={res['cohens_d']}"]

    return CaseReport(
        case_id=raw_req.get("case_id", "S_spatial_niche"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "niche_contrast": "stroma_adjacent vs stroma_poor", "target_output": norm["target_output"],
                              "readout": "EMT score (Vimentin − ECadherin)"},
        models_tools_selected={"engine": dec.engine, "tool": "squidpy imc (IMC 乳腺癌) + 空间 k-NN niche",
                               "method": "niche 分层 EMT 评分对比(间质邻接 vs 贫瘠)", "reason": dec.reason},
        raw_output={"niche_emt_shift": res},
        baseline_comparison={"baseline": "间质贫瘠 niche 的肿瘤 EMT 评分",
                             "stroma_adjacent_mean": res["mean_a"], "stroma_poor_mean": res["mean_b"],
                             "niche_effect_cohens_d": res["cohens_d"]},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "squidpy imc + niche scoring",
                             "source": "squidpy.datasets.imc (Jackson et al. 乳腺癌 IMC)",
                             "provenance_file": "data/cellstate/PROVENANCE_imc.json",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    ), dec

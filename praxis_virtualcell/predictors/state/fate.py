"""R1(v0.5):Stem/progenitor 分化 fate case —— 红系 vs 髓系 lineage fate 评分。

数据:paul15(Paul et al. 2015 小鼠髓系祖细胞分化)的 committed 子集
(`data/cellstate/paul15_fate_subset.json`,红系/髓系/其它 lineage × marker panels)。
分析:每 cell fate score = 红系 marker 评分 − 髓系 marker 评分 → 分离红系/髓系群(Cohen's d)。
复用 `scoring.py`。治理:marker 覆盖不足 → downgrade;分离弱 → downgrade/caution。

诚实:paul15 是**原生小鼠 scRNA**,marker 分析非 human→mouse predictor 迁移 → ortholog caution
**不适用**(route 的 mouse caution 针对 predictor 迁移,本 case 为原生 marker 评分)。不训练模型。
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.state.scoring import cohens_d, lognorm, panel_score

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "cellstate" / "paul15_fate_subset.json"
_D_ACCEPT, _D_CAUTION, _COV_MIN = 0.8, 0.3, 0.5
_BOUNDARY = ("fate 评分是 marker-based lineage 相对量(CP10k+log1p,红系−髓系),**非**绝对命运概率或"
             "pseudotime;paul15 小鼠祖细胞子集;marker/阈值为设定默认;downgrade 表'证据不足以定 lineage'。"
             "原生小鼠 marker 分析,非 human predictor 迁移(ortholog caution 不适用)。")


class FateDB:
    """paul15 fate 子集(committed):红系/髓系 marker + lineage 标注。"""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))
        self._panels = self._d["panels"]
        self._idx = {g: i for i, g in enumerate(self._d["gene_order"])}

    def marker_coverage(self, ery_panel=None, mye_panel=None) -> float:
        """两谱系 panel 覆盖的最小值(fate 需红系与髓系 marker 都够)。"""
        ery = ery_panel or self._panels["ery"]
        mye = mye_panel or self._panels["mye"]
        cov_e = sum(1 for g in ery if g in self._idx) / len(ery) if ery else 0.0
        cov_m = sum(1 for g in mye if g in self._idx) / len(mye) if mye else 0.0
        return min(cov_e, cov_m)

    def fate_score(self, cell, ery_panel=None, mye_panel=None) -> float | None:
        ln = lognorm(cell["counts"], cell["total_counts"])
        hk = [self._idx[g] for g in self._panels["hk"] if g in self._idx]
        ery = [self._idx[g] for g in (ery_panel or self._panels["ery"]) if g in self._idx]
        mye = [self._idx[g] for g in (mye_panel or self._panels["mye"]) if g in self._idx]
        es = panel_score(ln, ery, hk)
        ms = panel_score(ln, mye, hk)
        if es is None or ms is None:
            return None
        return es - ms                      # >0 偏红系

    def fate_separation(self, ery_panel=None, mye_panel=None) -> dict:
        ery, mye = [], []
        for c in self._d["cells"]:
            s = self.fate_score(c, ery_panel, mye_panel)
            if s is None:
                continue
            if c["lineage"] == "erythroid":
                ery.append(s)
            elif c["lineage"] == "myeloid":
                mye.append(s)
        return {"n_erythroid": len(ery), "n_myeloid": len(mye),
                "erythroid_mean": round(sum(ery) / len(ery), 3) if ery else None,
                "myeloid_mean": round(sum(mye) / len(mye), 3) if mye else None,
                "cohens_d": round(cohens_d(ery, mye), 3)}


def run_fate_case(raw_req: dict, db: FateDB | None = None, ery_panel=None, mye_panel=None):
    """Stem/progenitor 分化 fate case → 7 部分 CaseReport(真实 lineage 分离 + 受治理裁决)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "state_scoring":
        raise ValueError(f"fate case 期望 state_scoring,route 给了 {dec.engine}")
    db = db or FateDB()

    coverage = db.marker_coverage(ery_panel, mye_panel)
    sep = db.fate_separation(ery_panel, mye_panel)
    d = abs(sep["cohens_d"])
    if coverage < _COV_MIN:
        disposition, flags = "downgrade", [f"low_marker_coverage:{coverage:.2f}"]
    elif sep["n_erythroid"] < 2 or sep["n_myeloid"] < 2:
        disposition, flags = "abstain", ["insufficient_lineage_cells"]
    elif d >= _D_ACCEPT:
        disposition, flags = "accept", []
    elif d >= _D_CAUTION:
        disposition, flags = "caution", [f"moderate_separation:d={sep['cohens_d']}"]
    else:
        disposition, flags = "downgrade", [f"weak_separation:d={sep['cohens_d']}"]

    return CaseReport(
        case_id=raw_req.get("case_id", "S_paul15_fate"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "normalized_targets": norm["perturbation_targets"],
                              "target_output": norm["target_output"], "preprocessing": "CP10k + log1p",
                              "note": "原生小鼠 marker 分析,非 predictor 迁移(ortholog N/A)"},
        models_tools_selected={"engine": dec.engine, "tool": "paul15 (scanpy) + 红/髓系 lineage panel",
                               "method": "marker-based lineage fate 评分(红系−髓系)", "reason": dec.reason},
        raw_output={"marker_coverage": round(coverage, 3), "erythroid_mean": sep["erythroid_mean"],
                    "myeloid_mean": sep["myeloid_mean"], "cohens_d": sep["cohens_d"],
                    "n_erythroid": sep["n_erythroid"], "n_myeloid": sep["n_myeloid"]},
        baseline_comparison={"baseline": "两谱系 fate 评分对比(红系 vs 髓系)",
                             "erythroid_mean": sep["erythroid_mean"], "myeloid_mean": sep["myeloid_mean"],
                             "separation_cohens_d": sep["cohens_d"]},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "scanpy paul15 + fate scoring",
                             "source": "scanpy.datasets.paul15 (Paul et al. 2015)",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    ), dec

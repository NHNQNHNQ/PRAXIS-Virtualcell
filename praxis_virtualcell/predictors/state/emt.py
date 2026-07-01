"""R4(v0.5):Cancer EMT state 刻画 case —— 间质 vs 上皮 marker(填应用 3 例 3C)。

数据:mcfarland_2020(MIX-seq 泛癌 scRNA)的 committed 子集(`data/cellstate/mcfarland_emt_subset.json`,
间质/上皮/hk marker × 肉瘤/上皮癌/其它)。分析:EMT score = 间质 marker 评分 − 上皮 marker 评分 →
分离肉瘤(间质性)vs 上皮癌(Cohen's d)。复用 `scoring.py`。

诚实:mcfarland 无 TGF-β 等 EMT **诱导扰动** → 本 case 是 EMT **状态刻画**(哪类癌偏间质),
**非**扰动诱导的 EMT 转变(如实标注)。治理:marker 覆盖不足/分离弱 → downgrade。不训练模型。
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.state.scoring import cohens_d, lognorm, panel_score

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "cellstate" / "mcfarland_emt_subset.json"
_D_ACCEPT, _D_CAUTION, _COV_MIN = 0.8, 0.3, 0.5
_BOUNDARY = ("EMT score 是 marker-based 相对量(间质−上皮),**非**绝对 EMT 程度;mcfarland 泛癌子集;"
             "**无 EMT 诱导扰动 → 本 case 为 EMT 状态刻画(哪类癌偏间质),非扰动诱导的 EMT 转变**;"
             "marker/阈值为设定默认;downgrade 表'证据不足以定 EMT 状态'。")


class EmtDB:
    """mcfarland EMT 子集(committed):间质/上皮 marker + 癌类分组。"""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))
        self._panels = self._d["panels"]
        self._idx = {g: i for i, g in enumerate(self._d["gene_order"])}

    def marker_coverage(self, mes_panel=None, epi_panel=None) -> float:
        mes = mes_panel or self._panels["mes"]
        epi = epi_panel or self._panels["epi"]
        cov_m = sum(1 for g in mes if g in self._idx) / len(mes) if mes else 0.0
        cov_e = sum(1 for g in epi if g in self._idx) / len(epi) if epi else 0.0
        return min(cov_m, cov_e)

    def emt_score(self, cell, mes_panel=None, epi_panel=None) -> float | None:
        ln = lognorm(cell["counts"], cell["total_counts"])
        hk = [self._idx[g] for g in self._panels["hk"] if g in self._idx]
        mes = [self._idx[g] for g in (mes_panel or self._panels["mes"]) if g in self._idx]
        epi = [self._idx[g] for g in (epi_panel or self._panels["epi"]) if g in self._idx]
        ms = panel_score(ln, mes, hk)
        es = panel_score(ln, epi, hk)
        if ms is None or es is None:
            return None
        return ms - es                       # >0 偏间质

    def emt_separation(self, mes_panel=None, epi_panel=None) -> dict:
        mesc, epic = [], []
        for c in self._d["cells"]:
            s = self.emt_score(c, mes_panel, epi_panel)
            if s is None:
                continue
            if c["group"] == "mesenchymal_ca":
                mesc.append(s)
            elif c["group"] == "epithelial_ca":
                epic.append(s)
        return {"n_mesenchymal": len(mesc), "n_epithelial": len(epic),
                "mesenchymal_mean": round(sum(mesc) / len(mesc), 3) if mesc else None,
                "epithelial_mean": round(sum(epic) / len(epic), 3) if epic else None,
                "cohens_d": round(cohens_d(mesc, epic), 3)}


def run_emt_case(raw_req: dict, db: EmtDB | None = None, mes_panel=None, epi_panel=None):
    """Cancer EMT state 刻画 case → 7 部分 CaseReport(真实 EMT 分离 + 受治理裁决)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "state_scoring":
        raise ValueError(f"EMT case 期望 state_scoring,route 给了 {dec.engine}")
    db = db or EmtDB()

    coverage = db.marker_coverage(mes_panel, epi_panel)
    sep = db.emt_separation(mes_panel, epi_panel)
    d = abs(sep["cohens_d"])
    if coverage < _COV_MIN:
        disposition, flags = "downgrade", [f"low_marker_coverage:{coverage:.2f}"]
    elif sep["n_mesenchymal"] < 2 or sep["n_epithelial"] < 2:
        disposition, flags = "abstain", ["insufficient_group_cells"]
    elif d >= _D_ACCEPT:
        disposition, flags = "accept", []
    elif d >= _D_CAUTION:
        disposition, flags = "caution", [f"moderate_separation:d={sep['cohens_d']}"]
    else:
        disposition, flags = "downgrade", [f"weak_separation:d={sep['cohens_d']}"]

    return CaseReport(
        case_id=raw_req.get("case_id", "S_cancer_emt"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "normalized_targets": norm["perturbation_targets"],
                              "target_output": norm["target_output"], "preprocessing": "CP10k + log1p",
                              "note": "EMT 状态刻画(非扰动诱导 EMT 转变)"},
        models_tools_selected={"engine": dec.engine, "tool": "mcfarland_2020 (pertpy) + EMT marker panel",
                               "method": "marker-based EMT 评分(间质−上皮)", "reason": dec.reason},
        raw_output={"marker_coverage": round(coverage, 3), "mesenchymal_mean": sep["mesenchymal_mean"],
                    "epithelial_mean": sep["epithelial_mean"], "cohens_d": sep["cohens_d"],
                    "n_mesenchymal": sep["n_mesenchymal"], "n_epithelial": sep["n_epithelial"]},
        baseline_comparison={"baseline": "上皮癌 EMT 评分(vs 肉瘤/间质性)",
                             "mesenchymal_mean": sep["mesenchymal_mean"], "epithelial_mean": sep["epithelial_mean"],
                             "separation_cohens_d": sep["cohens_d"]},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "pertpy mcfarland_2020 + EMT scoring",
                             "source": "pertpy.data.mcfarland_2020 (MIX-seq)",
                             "provenance_file": "data/cellstate/PROVENANCE_mcfarland.json",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    ), dec

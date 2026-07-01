"""W5.3(v0.4,Phase II):Human 代谢通路 tendency case —— 表达 → 糖酵解/OXPHOS 活性(scFEA/Compass 思想)。

数据:Kang 2018 IFN-β PBMC 的代谢子集(`data/cellstate/kang_metabolic_subset.json`,glycolysis/oxphos/hk
panels)。分析:每 cell 归一 → 通路活性评分(panel−hk)→ ctrl vs stim 的 Cohen's d。

治理对照(R6 核心):**同一 IFN-β 扰动、同一批细胞**,ISG 激活强(d≈2.5 → accept,见 cell_state case),
但代谢通路 tendency 在**表达层信号弱**(d≈0.1-0.3 → downgrade)。agent 按证据**分别裁决**、不一刀切——
即"reliability-governed reporting prevents overclaiming":不为"跑通"而硬报一个不存在的代谢重编程。

科学默认:CP10k+log1p;panel = 教科书糖酵解/OXPHOS 基因;效应阈 accept |d|≥0.8 / caution 0.3 / 否则
downgrade;通路评分是**表达层代理**,非真实通量。
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.predictors.state.scoring import lognorm, panel_score, cohens_d

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "cellstate" / "kang_metabolic_subset.json"
_D_ACCEPT, _D_CAUTION = 0.8, 0.3
_BOUNDARY = ("通路活性评分是**表达层代理**(CP10k+log1p,panel−housekeeping),**非**真实代谢通量(需 "
             "scFEA/Compass/13C-flux 才是通量);Kang 2018 短时刺激 PBMC 子集;弱效应 downgrade 表'表达层"
             "无足够证据支持代谢重编程',非'代谢无变化'(可能后转录层)。")


class MetabolicDB:
    """Kang 代谢通路子集(committed):glycolysis / oxphos / hk panels。"""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))
        self._panels = self._d["panels"]
        self._idx = {g: i for i, g in enumerate(self._d["gene_order"])}

    def panels(self) -> list[str]:
        return [p for p in self._panels if p != "hk"]

    def score_cell(self, cell, panel: str) -> float | None:
        ln = lognorm(cell["counts"], cell["total_counts"])
        pidx = [self._idx[g] for g in self._panels[panel] if g in self._idx]
        hk = [self._idx[g] for g in self._panels["hk"] if g in self._idx]
        return panel_score(ln, pidx, hk)

    def pathway_shift(self, panel: str) -> dict:
        ctrl, stim = [], []
        for c in self._d["cells"]:
            s = self.score_cell(c, panel)
            if s is None:
                continue
            (stim if c["label"] == "stim" else ctrl).append(s)
        return {"panel": panel, "n_ctrl": len(ctrl), "n_stim": len(stim),
                "ctrl_mean": round(sum(ctrl) / len(ctrl), 4) if ctrl else None,
                "stim_mean": round(sum(stim) / len(stim), 4) if stim else None,
                "cohens_d": round(cohens_d(stim, ctrl), 3)}


def run_metabolic_tendency_case(raw_req: dict, db: MetabolicDB | None = None):
    """Human 代谢通路 tendency case → 7 部分 CaseReport(真实评分 + 受治理裁决)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "pathway_scoring":
        raise ValueError(f"metabolic tendency case 期望 pathway_scoring,route 给了 {dec.engine}")
    db = db or MetabolicDB()

    shifts = [db.pathway_shift(p) for p in db.panels()]
    max_d = max((abs(s["cohens_d"]) for s in shifts), default=0.0)
    if any(s["n_ctrl"] < 2 or s["n_stim"] < 2 for s in shifts):
        disposition, flags = "abstain", ["no_ctrl_or_stim_group"]
    elif max_d >= _D_ACCEPT:
        disposition, flags = "accept", []
    elif max_d >= _D_CAUTION:
        disposition, flags = "caution", [f"moderate_pathway_effect:max_d={max_d}"]
    else:
        disposition, flags = "downgrade", [f"weak_pathway_effect:max_d={max_d}"]

    return CaseReport(
        case_id=raw_req.get("case_id", "S_ifn_metabolic_tendency"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "normalized_targets": norm["perturbation_targets"],
                              "target_output": norm["target_output"], "preprocessing": "CP10k + log1p"},
        models_tools_selected={"engine": dec.engine, "tool": "Kang 2018 + 代谢通路 panel(糖酵解/OXPHOS)",
                               "method": "表达层代谢通路活性评分(scFEA/Compass 思想)", "reason": dec.reason},
        raw_output={"pathway_shifts": shifts, "max_abs_cohens_d": round(max_d, 3)},
        baseline_comparison={"baseline": "unstimulated (ctrl) 通路活性评分",
                             "contrast_note": "对照 cell_state ISG 激活(同扰动 d≈2.5 accept):代谢层 d 弱 → 分别裁决"},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "pertpy Kang 2018 + pathway scoring",
                             "source": "pertpy.data.kang_2018 (GSE96583)",
                             "provenance_file": "data/cellstate/PROVENANCE.json",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    ), dec

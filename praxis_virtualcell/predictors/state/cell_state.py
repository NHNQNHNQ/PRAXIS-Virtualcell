"""W5.2(v0.4,Phase II):Human 免疫激活 cell-state case —— IFN-β 刺激 → ISG 激活 state 迁移。

数据:Kang 2018 IFN-β PBMC(pertpy `pt.data.kang_2018`)的 committed 子集
(`data/cellstate/kang_isg_subset.json`,2232 cells × 25 ISG + 8 housekeeping 基因,原始 counts;
provenance `data/cellstate/PROVENANCE.json`)。

分析:每 cell 归一(CP10k+log1p)→ **ISG 激活评分 = mean(ISG) − mean(housekeeping)** → ctrl vs stim
的 state 迁移(Cohen's d + 阈值分类准确率)。治理(R6):marker 覆盖不足 → downgrade;迁移不显著
(|d| 小)→ downgrade/caution;无 ctrl/stim 分组 → abstain。**不训练模型**,纯评分 + 受治理裁决。

科学默认(写明依据):CP10k+log1p(scRNA 标准);ISG panel = 教科书 type-I IFN 响应基因;
效应阈 accept d≥0.8 / caution 0.3≤d<0.8 / downgrade d<0.3;marker 覆盖阈 0.5。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents.route_table import route

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "cellstate" / "kang_isg_subset.json"

# 教科书 type-I 干扰素刺激基因(ISG)
ISG_PANEL = ["ISG15", "IFI6", "IFI27", "IFI44", "IFI44L", "IFIT1", "IFIT3", "ISG20", "MX1", "MX2",
             "OAS1", "OAS2", "OAS3", "RSAD2", "STAT1", "STAT2", "IRF7", "LY6E", "IFITM3", "BST2",
             "XAF1", "USP18", "HERC5", "EPSTI1", "CMPK2"]

_D_ACCEPT, _D_CAUTION, _COV_MIN = 0.8, 0.3, 0.5
_BOUNDARY = ("ISG 激活评分是 marker-based 相对量(CP10k+log1p,ISG−housekeeping),**非**绝对通路活性;"
             "Kang 2018 是 PBMC scRNA 子集(2232 cells);效应/阈值为设定默认;downgrade 表'证据不足以"
             "确证 state 迁移',非'无迁移'。")


def _cohens_d(a: list[float], b: list[float]) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    psd = math.sqrt((va + vb) / 2) or 1e-9
    return (ma - mb) / psd


class CellStateDB:
    """Kang 2018 ISG 子集(committed)。提供归一 + ISG 激活评分。"""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))
        self._isg = self._d["genes_isg"]
        self._hk = self._d["genes_hk"]
        self._idx = {g: i for i, g in enumerate(self._isg + self._hk)}

    def _lognorm(self, cell) -> list[float]:
        tot = cell["total_counts"] or 1.0
        return [math.log1p(c / tot * 1e4) for c in cell["counts"]]

    def score_cell(self, cell, isg_panel=None) -> float | None:
        """ISG 激活评分 = mean(ISG present) − mean(housekeeping)。panel 覆盖为空 → None。"""
        ln = self._lognorm(cell)
        isg = [self._idx[g] for g in (isg_panel or self._isg) if g in self._idx]
        hk = [self._idx[g] for g in self._hk if g in self._idx]
        if not isg or not hk:
            return None
        return sum(ln[i] for i in isg) / len(isg) - sum(ln[i] for i in hk) / len(hk)

    def marker_coverage(self, isg_panel=None) -> float:
        panel = isg_panel or self._isg
        return sum(1 for g in panel if g in self._idx) / len(panel) if panel else 0.0

    def state_shift(self, isg_panel=None, cell_type=None) -> dict:
        """ctrl vs stim 的 ISG 评分迁移(整体或指定 cell_type)。"""
        ctrl, stim = [], []
        for c in self._d["cells"]:
            if cell_type and c["cell_type"] != cell_type:
                continue
            s = self.score_cell(c, isg_panel)
            if s is None:
                continue
            (stim if c["label"] == "stim" else ctrl).append(s)
        d = _cohens_d(stim, ctrl)
        return {"n_ctrl": len(ctrl), "n_stim": len(stim),
                "ctrl_mean": round(sum(ctrl) / len(ctrl), 4) if ctrl else None,
                "stim_mean": round(sum(stim) / len(stim), 4) if stim else None,
                "cohens_d": round(d, 3)}

    def cell_types(self) -> list[str]:
        return sorted({c["cell_type"] for c in self._d["cells"]})


def run_cellstate_case(raw_req: dict, db: CellStateDB | None = None, isg_panel=None):
    """Human 免疫激活 cell-state case → 7 部分 CaseReport(真实 state 迁移 + 受治理裁决)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "state_scoring":
        raise ValueError(f"cell-state case 期望 state_scoring,route 给了 {dec.engine}")
    db = db or CellStateDB()

    coverage = db.marker_coverage(isg_panel)
    overall = db.state_shift(isg_panel)
    per_ct = [{"cell_type": ct, **db.state_shift(isg_panel, cell_type=ct)} for ct in db.cell_types()]

    d = abs(overall["cohens_d"])
    if overall["n_ctrl"] < 2 or overall["n_stim"] < 2:
        disposition, flags = "abstain", ["no_ctrl_or_stim_group"]
    elif coverage < _COV_MIN:
        disposition, flags = "downgrade", [f"low_marker_coverage:{coverage:.2f}"]
    elif d >= _D_ACCEPT:
        disposition, flags = "accept", []
    elif d >= _D_CAUTION:
        disposition, flags = "caution", [f"moderate_effect:d={overall['cohens_d']}"]
    else:
        disposition, flags = "downgrade", [f"weak_effect:d={overall['cohens_d']}"]

    report = CaseReport(
        case_id=raw_req.get("case_id", "S_ifn_activation"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "normalized_targets": norm["perturbation_targets"],
                              "target_output": norm["target_output"], "preprocessing": "CP10k + log1p"},
        models_tools_selected={"engine": dec.engine, "tool": "Kang 2018 IFN-β PBMC (pertpy) + ISG panel",
                               "method": "marker-based ISG activation scoring", "reason": dec.reason},
        raw_output={"marker_coverage": round(coverage, 3), "isg_panel_size": len(isg_panel or ISG_PANEL),
                    "ctrl_mean": overall["ctrl_mean"], "stim_mean": overall["stim_mean"],
                    "cohens_d": overall["cohens_d"], "n_ctrl": overall["n_ctrl"], "n_stim": overall["n_stim"],
                    "per_cell_type": per_ct},
        baseline_comparison={"baseline": "unstimulated (ctrl) ISG activation score",
                             "ctrl_mean": overall["ctrl_mean"], "stim_mean": overall["stim_mean"],
                             "state_shift_cohens_d": overall["cohens_d"]},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "pertpy Kang 2018 + scanpy-style scoring",
                             "source": "pertpy.data.kang_2018 (Kang et al. 2018, GSE96583)",
                             "provenance_file": "data/cellstate/PROVENANCE.json",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    )
    return report, dec

"""IFN-beta immune-state analysis in the committed Kang 2018 PBMC subset: 2232 cells, 25 ISGs, 8 housekeeping
genes. Normalize CP10k+log1p and compute mean(ISG)−mean(housekeeping), then ctrl/stim Cohen's d and threshold
accuracy. Missing groups abstain; low marker coverage or weak shifts downgrade/caution. Defaults: accept d≥0.8,
caution 0.3≤d<0.8, downgrade d<0.3, coverage threshold 0.5. No model is trained.
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.state.scoring import cohens_d as _cohens_d
from praxis_virtualcell.predictors.state.scoring import lognorm, panel_score

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "cellstate" / "kang_isg_subset.json"


ISG_PANEL = ["ISG15", "IFI6", "IFI27", "IFI44", "IFI44L", "IFIT1", "IFIT3", "ISG20", "MX1", "MX2",
             "OAS1", "OAS2", "OAS3", "RSAD2", "STAT1", "STAT2", "IRF7", "LY6E", "IFITM3", "BST2",
             "XAF1", "USP18", "HERC5", "EPSTI1", "CMPK2"]

_D_ACCEPT, _D_CAUTION, _COV_MIN = 0.8, 0.3, 0.5
_BOUNDARY = (
    'ISG activation is a relative marker score (CP10k+log1p, ISG−housekeeping), not '
    'absolute pathway activity; Kang 2018 is a PBMC scRNA subset (2232 cells); '
    'effects/thresholds are configured defaults; downgrade means insufficient evidence to '
    'establish a state shift, not absence of a shift.'
)


class CellStateDB:
    """Committed Kang 2018 ISG subset with normalization and activation scoring."""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))
        self._isg = self._d["genes_isg"]
        self._hk = self._d["genes_hk"]
        self._idx = {g: i for i, g in enumerate(self._isg + self._hk)}

    def score_cell(self, cell, isg_panel=None) -> float | None:
        """Compute mean(present ISGs)−mean(housekeeping); absent panel coverage returns None."""
        ln = lognorm(cell["counts"], cell["total_counts"])
        isg = [self._idx[g] for g in (isg_panel or self._isg) if g in self._idx]
        hk = [self._idx[g] for g in self._hk if g in self._idx]
        return panel_score(ln, isg, hk)

    def marker_coverage(self, isg_panel=None) -> float:
        panel = isg_panel or self._isg
        return sum(1 for g in panel if g in self._idx) / len(panel) if panel else 0.0

    def state_shift(self, isg_panel=None, cell_type=None) -> dict:
        """Compare ctrl/stim ISG scores for all cells or one cell_type."""
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
    """Return a 7-part human immune-state case report with observed shifts and governance."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "state_scoring":
        raise ValueError(f"cell-state case expected state_scoring; routing selected {dec.engine}")
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

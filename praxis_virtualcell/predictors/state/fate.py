"""Erythroid-minus-myeloid fate-marker analysis in native mouse paul15 progenitors (Paul et al. 2015). Compare
lineage groups with Cohen's d; weak coverage/separation downgrades/cautions. This is native mouse marker
scoring, so human-to-mouse predictor-transfer ortholog caution is inapplicable. No model is trained.
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
_BOUNDARY = (
    'Fate score is a relative marker-based lineage measure (CP10k+log1p, '
    'erythroid−myeloid), not absolute fate probability or pseudotime; paul15 is a mouse '
    'progenitor subset; markers/thresholds are configured defaults; downgrade indicates '
    'insufficient lineage evidence.Native mouse marker analysis, not human predictor '
    'transfer (ortholog caution is inapplicable).'
)


class FateDB:
    """Committed paul15 erythroid/myeloid marker subset with lineage annotations."""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))
        self._panels = self._d["panels"]
        self._idx = {g: i for i, g in enumerate(self._d["gene_order"])}

    def marker_coverage(self, ery_panel=None, mye_panel=None) -> float:
        """Return the smaller of the two lineage panel coverage values; both panels are required."""
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
        return es - ms

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
    """Return a 7-part progenitor fate report with observed lineage separation and governance."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "state_scoring":
        raise ValueError(f"fate case expected state_scoring; routing selected {dec.engine}")
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
                              "note": "Native mouse marker analysis, not predictor transfer (ortholog N/A)"},
        models_tools_selected={"engine": dec.engine, "tool": "paul15 (scanpy) + erythroid/myeloid lineage panels",
                               "method": "Marker-based lineage fate score (erythroid−myeloid)", "reason": dec.reason},
        raw_output={"marker_coverage": round(coverage, 3), "erythroid_mean": sep["erythroid_mean"],
                    "myeloid_mean": sep["myeloid_mean"], "cohens_d": sep["cohens_d"],
                    "n_erythroid": sep["n_erythroid"], "n_myeloid": sep["n_myeloid"]},
        baseline_comparison={"baseline": "Two-lineage fate score comparison (erythroid vs myeloid)",
                             "erythroid_mean": sep["erythroid_mean"], "myeloid_mean": sep["myeloid_mean"],
                             "separation_cohens_d": sep["cohens_d"]},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "scanpy paul15 + fate scoring",
                             "source": "scanpy.datasets.paul15 (Paul et al. 2015)",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    ), dec

"""EMT state characterization in committed mcfarland_2020 MIX-seq pan-cancer data. Compute
mesenchymal-minus-epithelial marker scores and compare sarcoma with epithelial carcinoma using Cohen's d. No
TGF-beta/EMT-inducing perturbation is present, so this characterizes state rather than induced transition. Weak
coverage/separation downgrades; no model is trained.
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
_BOUNDARY = (
    'EMT score is a relative marker measure (mesenchymal−epithelial), not absolute EMT '
    'degree; mcfarland is a pan-cancer subset; without an EMT-inducing perturbation this '
    'case characterizes EMT state (mesenchymal cancer types), not perturbation-induced '
    'EMT transition; markers/thresholds are configured defaults; downgrade indicates '
    'insufficient evidence to establish EMT state.'
)


class EmtDB:
    """Committed mcfarland EMT marker subset with cancer-type groups."""

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
        return ms - es

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
    """Return a 7-part cancer EMT-state report with observed separation and governance."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "state_scoring":
        raise ValueError(f"EMT case expected state_scoring; routing selected {dec.engine}")
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
                              "note": "EMT state characterization (not perturbation-induced EMT transition)"},
        models_tools_selected={"engine": dec.engine, "tool": "mcfarland_2020 (pertpy) + EMT marker panel",
                               "method": "Marker-based EMT score (mesenchymal−epithelial)", "reason": dec.reason},
        raw_output={"marker_coverage": round(coverage, 3), "mesenchymal_mean": sep["mesenchymal_mean"],
                    "epithelial_mean": sep["epithelial_mean"], "cohens_d": sep["cohens_d"],
                    "n_mesenchymal": sep["n_mesenchymal"], "n_epithelial": sep["n_epithelial"]},
        baseline_comparison={"baseline": "Epithelial carcinoma EMT score (vs sarcoma/mesenchymal state)",
                             "mesenchymal_mean": sep["mesenchymal_mean"], "epithelial_mean": sep["epithelial_mean"],
                             "separation_cohens_d": sep["cohens_d"]},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "pertpy mcfarland_2020 + EMT scoring",
                             "source": "pertpy.data.mcfarland_2020 (MIX-seq)",
                             "provenance_file": "data/cellstate/PROVENANCE_mcfarland.json",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    ), dec

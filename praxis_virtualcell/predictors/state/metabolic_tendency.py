"""Expression-level glycolysis/OXPHOS proxy analysis in the Kang 2018 IFN-beta subset. Normalize per cell, compute
panel-minus-housekeeping scores, and compare ctrl/stim with Cohen's d. The same cells show strong ISG activation
(d≈2.5) but weak metabolic expression effects (d≈0.1–0.3), requiring separate verdicts. Defaults: CP10k+log1p,
accept |d|≥0.8, caution 0.3, otherwise downgrade. Scores are expression proxies, not measured flux.
"""

from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.state.scoring import cohens_d, lognorm, panel_score

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "cellstate" / "kang_metabolic_subset.json"
_D_ACCEPT, _D_CAUTION = 0.8, 0.3
_BOUNDARY = (
    "Pathway scores are expression-level proxies (CP10k+log1p, panel−housekeeping), not "
    "measured metabolic flux (which requires scFEA/Compass/13C-flux analysis); Kang 2018 "
    "is a briefly stimulated PBMC subset; weak-effect downgrade means insufficient "
    "expression-level evidence of metabolic reprogramming, not unchanged metabolism "
    "(post-transcriptional effects may remain)."
)


class MetabolicDB:
    """Committed Kang glycolysis/oxphos/housekeeping pathway subset."""

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
        return {
            "panel": panel,
            "n_ctrl": len(ctrl),
            "n_stim": len(stim),
            "ctrl_mean": round(sum(ctrl) / len(ctrl), 4) if ctrl else None,
            "stim_mean": round(sum(stim) / len(stim), 4) if stim else None,
            "cohens_d": round(cohens_d(stim, ctrl), 3),
        }


def run_metabolic_tendency_case(raw_req: dict, db: MetabolicDB | None = None):
    """Return a 7-part human metabolic-tendency report with observed scores and governance."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "pathway_scoring":
        raise ValueError(f"metabolic tendency case expected pathway_scoring; routing selected {dec.engine}")
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
        object_normalization={
            "species": norm["species"],
            "perturbation_object": norm["perturbation_object"],
            "normalized_targets": norm["perturbation_targets"],
            "target_output": norm["target_output"],
            "preprocessing": "CP10k + log1p",
        },
        models_tools_selected={
            "engine": dec.engine,
            "tool": "Kang 2018 + metabolic pathway panels (glycolysis/OXPHOS)",
            "method": "Expression-level metabolic pathway scoring (inspired by scFEA/Compass)",
            "reason": dec.reason,
        },
        raw_output={"pathway_shifts": shifts, "max_abs_cohens_d": round(max_d, 3)},
        baseline_comparison={
            "baseline": "Unstimulated (ctrl) pathway score",
            "contrast_note": (
                "Compare cell_state ISG activation (same perturbation, d≈2.5, accept): weak metabolic "
                "effects receive an independent verdict"
            ),
        },
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={
            "tool": "pertpy Kang 2018 + pathway scoring",
            "source": "pertpy.data.kang_2018 (GSE96583)",
            "provenance_file": "data/cellstate/PROVENANCE.json",
            "rules_hit": [dec.reason],
            "boundary": _BOUNDARY,
        },
    ), dec

"""Spatial niche EMT analysis from the squidpy breast cancer IMC subset. Niche labels use stromal fractions in
spatial k-NN neighborhoods: stroma_adjacent/stroma_poor/intermediate. Score=Vimentin−ECadherin; compare tumor
groups with Cohen's d. Strong/moderate/weak niche evidence accepts/cautions/downgrades; insufficient cells
abstain. Stromal EMT induction is a testable interpretation, without model training.
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
_BOUNDARY = (
    "EMT niche score = Vimentin − ECadherin (arcsinh IMC protein expression), not an "
    "absolute EMT degree; niches use stromal fractions in spatial k-NN neighborhoods; imc "
    "is one breast cancer sample; downgrade/caution denotes weak/moderate niche effects; "
    "greater mesenchymal character of stroma-adjacent tumors is a testable hypothesis of "
    "stromal EMT induction."
)


class SpatialNicheDB:
    """Committed IMC tumor/niche subset with Vimentin and ECadherin."""

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
        return {
            "niche_a": niche_a,
            "niche_b": niche_b,
            "n_a": len(a),
            "n_b": len(b),
            "mean_a": round(sum(a) / len(a), 3) if a else None,
            "mean_b": round(sum(b) / len(b), 3) if b else None,
            "cohens_d": round(cohens_d(a, b), 3),
        }


def run_spatial_niche_case(raw_req: dict, db: SpatialNicheDB | None = None):
    """Return a 7-part spatial niche report with observed differences and governance."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "spatial_niche":
        raise ValueError(f"spatial niche case expected spatial_niche; routing selected {dec.engine}")
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
        object_normalization={
            "species": norm["species"],
            "perturbation_object": norm["perturbation_object"],
            "niche_contrast": "stroma_adjacent vs stroma_poor",
            "target_output": norm["target_output"],  # noqa: E501
            "readout": "EMT score (Vimentin − ECadherin)",
        },
        models_tools_selected={
            "engine": dec.engine,
            "tool": "squidpy imc (breast cancer IMC) + spatial k-NN niche",
            "method": "Niche-stratified EMT score comparison (stroma-adjacent vs stroma-poor)",
            "reason": dec.reason,
        },
        raw_output={"niche_emt_shift": res},
        baseline_comparison={
            "baseline": "Tumor EMT score in stroma-poor niches",
            "stroma_adjacent_mean": res["mean_a"],
            "stroma_poor_mean": res["mean_b"],
            "niche_effect_cohens_d": res["cohens_d"],
        },
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={
            "tool": "squidpy imc + niche scoring",
            "source": "squidpy.datasets.imc (Jackson et al. breast cancer IMC)",
            "provenance_file": "data/cellstate/PROVENANCE_imc.json",
            "rules_hit": [dec.reason],
            "boundary": _BOUNDARY,
        },
    ), dec

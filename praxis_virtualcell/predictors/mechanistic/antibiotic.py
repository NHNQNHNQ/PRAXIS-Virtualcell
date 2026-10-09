"""Antibiotic target-reaction inhibition in genome-scale E. coli iML1515 using GemModel. Knock out declared
metabolic target reactions and solve FBA. Nonmetabolic targets such as gyrase/cell wall or unknown targets
abstain because the metabolic model cannot represent them. No model is trained.
"""

from __future__ import annotations

from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.mechanistic.gem_model import GemModel

_IML1515 = Path(__file__).resolve().parents[3] / "data" / "gems" / "iML1515.xml.gz"


ANTIBIOTIC_TARGETS = {
    "trimethoprim": "DHFR",
    "sulfamethoxazole": "DHPS2",
    "sulfamethazine": "DHPS2",
    "ciprofloxacin": None,
    "ampicillin": None,
}
_BOUNDARY = (
    "FBA growth is a constrained optimal flux ratio under steady state, not absolute "
    "growth or MIC. Antibiotics are modeled as complete inhibition of target metabolic "
    "reactions (idealized). iML1515 covers metabolism; nonmetabolic targets (gyrase/cell "
    "wall) are unsupported and cause abstention; in-silico results require experimental "
    "confirmation."
)

_gem_cache = {}


def _gem() -> GemModel:
    if "iml" not in _gem_cache:
        _gem_cache["iml"] = GemModel(str(_IML1515))
    return _gem_cache["iml"]


def run_antibiotic_case(raw_req: dict, gem: GemModel | None = None):
    """Return a 7-part bacterial antibiotic-growth case report with actual target-inhibition FBA and governance."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "gem_fba":
        raise ValueError(f"antibiotic case expected gem_fba; routing selected {dec.engine}")
    gem = gem or _gem()

    results, dispositions, flags = [], [], []
    for ab in norm["perturbation_targets"]:
        key = ab.lower()
        if key not in ANTIBIOTIC_TARGETS:
            results.append({"antibiotic": ab, "target_rxn": None, "known": False})
            dispositions.append("abstain")
            flags.append(f"unknown_antibiotic:{ab}")
            continue
        rxn = ANTIBIOTIC_TARGETS[key]
        if rxn is None:
            results.append({"antibiotic": ab, "target_rxn": "non-metabolic", "known": True, "in_model": False})
            dispositions.append("abstain")
            flags.append(f"non_metabolic_target:{ab}")
            continue
        if not gem.model.reactions.has_id(rxn):
            results.append({"antibiotic": ab, "target_rxn": rxn, "in_model": False})
            dispositions.append("abstain")
            flags.append(f"target_rxn_not_in_model:{rxn}")
            continue
        with gem.model:
            gem.model.reactions.get_by_id(rxn).knock_out()
            g = max(float(gem.model.slim_optimize()), 0.0)
        ratio = g / gem.wt_growth if gem.wt_growth else 0.0
        results.append(
            {
                "antibiotic": ab,
                "target_rxn": rxn,
                "in_model": True,
                "growth": round(g, 5),
                "ratio_vs_wt": round(ratio, 4),
                "growth_arrest": g < 1e-6,
            }
        )
        dispositions.append("accept")

    order = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3}
    disposition = max(dispositions, key=lambda x: order[x]) if dispositions else "abstain"

    return CaseReport(
        case_id=raw_req.get("case_id", "S_ecoli_antibiotic"),
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"],
            "perturbation_object": norm["perturbation_object"],
            "normalized_targets": norm["perturbation_targets"],
            "target_output": norm["target_output"],
        },  # noqa: E501
        models_tools_selected={
            "engine": dec.engine,
            "tool": "cobrapy iML1515 (genome-scale E. coli)",
            "method": "FBA with antibiotic target metabolic reaction inhibition",
            "reason": dec.reason,
        },
        raw_output={"wt_growth": round(gem.wt_growth, 5), "antibiotics": results},
        baseline_comparison={
            "baseline": "WT growth (without antibiotic)",
            "wt_growth": round(gem.wt_growth, 5),
            "n_growth_arrest": sum(1 for r in results if r.get("growth_arrest")),
        },
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={
            "tool": "cobrapy",
            "model": "iML1515",
            "objective": "biomass FBA",
            "rules_hit": [dec.reason],
            "boundary": _BOUNDARY,
        },
    ), dec

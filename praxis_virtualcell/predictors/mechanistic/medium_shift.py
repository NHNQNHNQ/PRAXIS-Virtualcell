"""Environmental medium/carbon-source growth case using e_coli_core FBA. Replace glucose with a single carbon
source such as acetate/succinate. Missing exchanges abstain and partial availability cautions. Default uptake
bound is -10 mmol/gDW/h with oxygen open; WT reference is glucose minimal medium.
"""
from __future__ import annotations

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

CARBON_EXCHANGES = {
    "glucose": "EX_glc__D_e",
    "fructose": "EX_fru_e",
    "acetate": "EX_ac_e",
    "succinate": "EX_succ_e",
    "lactate": "EX_lac__D_e",
    "akg": "EX_akg_e",
    "alpha-ketoglutarate": "EX_akg_e",
    "pyruvate": "EX_pyr_e",
}
_GLUCOSE_EX = "EX_glc__D_e"
_UPTAKE_LB = -10.0

_BOUNDARY = (
    'FBA growth is a relative constrained optimal flux measure (steady state, '
    'single-carbon bound -10, aerobic), not an absolute growth rate. e_coli_core covers '
    'core metabolism and common carbon sources; absent model exchanges cause abstention, '
    'indicating that this reconstruction cannot assess the source rather than that the '
    'source is unusable.'
)


def carbon_growth(gem, carbon_name: str, uptake_lb: float = _UPTAKE_LB) -> float | None:
    """Change the carbon source and return FBA growth; absent source exchange returns None."""
    ex = CARBON_EXCHANGES.get(str(carbon_name).strip().lower())
    if ex is None or not gem.model.reactions.has_id(ex):
        return None
    with gem.model:
        if gem.model.reactions.has_id(_GLUCOSE_EX):
            gem.model.reactions.get_by_id(_GLUCOSE_EX).lower_bound = 0.0
        gem.model.reactions.get_by_id(ex).lower_bound = uptake_lb
        return max(float(gem.model.slim_optimize()), 0.0)


def run_medium_shift_case(raw_req: dict, gem=None):
    """Return a 7-part microbial medium-shift FBA report with RouteDecision."""
    from praxis_virtualcell.predictors.mechanistic.ecoli_gem import EcoliGEM

    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "gem_fba":
        raise ValueError(f"medium-shift case expected gem_fba; routing selected {dec.engine}")
    gem = gem or EcoliGEM()

    glucose_growth = carbon_growth(gem, "glucose") or gem.wt_growth
    rows, missing = [], []
    for c in norm["perturbation_targets"]:
        g = carbon_growth(gem, c)
        if g is None:
            missing.append(c)
            rows.append({"carbon": c, "in_model": False, "growth": None, "ratio_vs_glucose": None})
        else:
            rows.append({"carbon": c, "in_model": True, "growth": round(g, 5),
                         "ratio_vs_glucose": round(g / glucose_growth, 4) if glucose_growth else None})

    n_ok = sum(1 for r in rows if r["in_model"])
    if n_ok == 0:
        disposition, flags = "abstain", ["all_carbon_sources_not_in_model"]
    elif missing:
        disposition, flags = "caution", [f"carbon_not_in_model:{missing}"]
    else:
        disposition, flags = "accept", []

    report = CaseReport(
        case_id=raw_req.get("case_id", "S_ecoli_carbon_shift"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "normalized_targets": norm["perturbation_targets"],
                              "target_output": norm["target_output"]},
        models_tools_selected={"engine": dec.engine, "tool": "cobrapy e_coli_core (textbook)",
                               "method": "FBA single-carbon medium shift", "reason": dec.reason},
        raw_output={"reference": "glucose minimal", "glucose_growth": round(glucose_growth, 5),
                    "carbon_sources": rows},
        baseline_comparison={"baseline": "glucose minimal growth", "glucose_growth": round(glucose_growth, 5),
                             "n_in_model": n_ok, "n_missing": len(missing)},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "cobrapy", "model": "e_coli_core (textbook)", "objective": "biomass FBA",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    )
    return report, dec

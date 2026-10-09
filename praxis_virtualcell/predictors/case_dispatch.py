"""Dispatch engines to actual case runners and map CaseReport to delta. Support microbial gene/medium/antibiotic
growth, human drug signatures, and narrowly gated IFN-beta state scoring. Ligand embedding without a connected
model and unsupported state/species combinations abstain; additional supported paths are explicit branches.
"""

from __future__ import annotations

import os

from praxis_virtualcell.core.exceptions import UnsupportedEngine

REAL_ENGINES = frozenset({"gem_fba", "pathway_scoring", "embedding", "state_scoring"})


def _gears_importable() -> bool:
    """Probe torch/GEARS imports without loading checkpoints or running inference; missing dependencies return
    False.
    """
    import importlib.util

    return importlib.util.find_spec("torch") is not None and importlib.util.find_spec("gears") is not None


def gears_available() -> bool:
    """Real GEARS requires nonempty GEARS_CKPT and importable torch/gears. The check is deterministic and
    side-effect-free; absent prerequisites leave the legacy donor branch on its declared mock path.
    """
    return bool(os.environ.get("GEARS_CKPT")) and _gears_importable()


_GENE_LIKE = frozenset({"gene", "gene_combination"})


_IFN_BETA_ALIASES = frozenset(
    {
        "ifnb1",
        "ifnb",
        "ifn-b1",
        "ifnβ",
        "ifn-β",
        "ifn-beta",
        "ifnbeta",
        "interferon beta",
        "interferon-beta",
        "interferon β",
        "interferon beta 1",
        "interferon-beta-1",
    }
)


def _is_ifn_beta(targets) -> bool:

    ts = [str(t).strip().lower() for t in (targets or [])]
    return bool(ts) and all(t in _IFN_BETA_ALIASES for t in ts)


def dispatch_runner(engine: str, raw_req: dict):
    """Select a callable case runner from engine and request context; it returns (CaseReport, RouteDecision)."""
    species = raw_req.get("species")
    obj = raw_req.get("perturbation_object")
    if engine == "gem_fba":
        if obj in _GENE_LIKE:
            if species == "bacteria":
                from praxis_virtualcell.predictors.mechanistic.ecoli_gem import run_ecoli_growth_case

                return run_ecoli_growth_case
            if species == "yeast":
                from praxis_virtualcell.predictors.mechanistic.yeast_gem import run_yeast_growth_case

                return run_yeast_growth_case
        elif obj == "medium" and species == "bacteria":
            from praxis_virtualcell.predictors.mechanistic.medium_shift import run_medium_shift_case

            return run_medium_shift_case
        elif obj == "drug" and species == "bacteria":
            from praxis_virtualcell.predictors.mechanistic.antibiotic import run_antibiotic_case

            return run_antibiotic_case
    elif engine == "pathway_scoring":
        if species == "human" and _is_ifn_beta(raw_req.get("perturbation_targets")):
            from praxis_virtualcell.predictors.state.metabolic_tendency import run_metabolic_tendency_case

            return run_metabolic_tendency_case

    elif engine == "embedding":
        if raw_req.get("species") == "human" and obj == "drug":
            if raw_req.get("perturbation_dose") is not None:
                from praxis_virtualcell.predictors.embedding.drug_dose import run_drug_dose_case

                return run_drug_dose_case
            from praxis_virtualcell.predictors.embedding.drug_signature import run_drug_response_case

            return run_drug_response_case

    elif engine == "state_scoring":
        if raw_req.get("species") == "human" and _is_ifn_beta(raw_req.get("perturbation_targets")):
            from praxis_virtualcell.predictors.state.cell_state import run_cellstate_case

            return run_cellstate_case

    elif engine == "donor_predictor":
        if (
            species == "human"
            and obj in _GENE_LIKE
            and raw_req.get("target_output") == "expression"
            and gears_available()
        ):
            from praxis_virtualcell.predictors.ml.gears_case import run_gears_case

            return run_gears_case

    raise UnsupportedEngine(f"no case runner is connected: engine={engine} object={obj} species={species}")


def map_case_delta(engine: str, report) -> list[float]:
    """Deterministically map CaseReport.raw_output to a delta vector using discriminating keys and its existing
    rounding.
    """
    raw = report.raw_output
    if engine == "gem_fba":
        if "knockouts" in raw:
            return [round(k["ratio"] - 1.0, 4) for k in raw["knockouts"] if k["ratio"] is not None]
        if "carbon_sources" in raw:
            return [round(r["ratio_vs_glucose"] - 1.0, 4) for r in raw["carbon_sources"] if r["in_model"]]
        if "antibiotics" in raw:
            return [
                round(r["ratio_vs_wt"] - 1.0, 4)
                for r in raw["antibiotics"]
                if r.get("in_model") and r.get("ratio_vs_wt") is not None
            ]
        raise UnsupportedEngine(f"gem_fba map_case_delta does not support raw_output shape: {sorted(raw)}")
    if engine == "pathway_scoring":
        return [round(s["cohens_d"], 4) for s in report.raw_output["pathway_shifts"]]
    if engine == "embedding":
        if "per_drug" in raw:
            return [
                round(d["moa_enrichment"], 4)
                for d in raw["per_drug"]
                if d.get("in_db") and d.get("moa_enrichment") is not None
            ]
        if "dose_response" in raw:
            dr = raw["dose_response"]
            return [round(dr["spearman"], 4)] if dr is not None else []
        raise UnsupportedEngine(f"embedding map_case_delta does not support raw_output shape: {sorted(raw)}")
    if engine == "state_scoring":
        if "per_cell_type" in report.raw_output:
            return [round(report.raw_output["cohens_d"], 4)]
        raise UnsupportedEngine(
            f"state_scoring map_case_delta does not support raw_output shape: {sorted(report.raw_output)}"
        )
    if engine == "donor_predictor":
        if "gears_delta" in raw:
            return list(raw["gears_delta"])
        raise UnsupportedEngine(f"donor_predictor map_case_delta does not support raw_output shape: {sorted(raw)}")
    raise UnsupportedEngine(f"map_case_delta does not support engine={engine}")

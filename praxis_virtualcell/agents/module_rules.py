"""Pure deterministic mapping from normalized requests to primary/secondary modules and mismatch queries. Engine
ownership follows route_table and MODULES. Optional LLM suggestions must remain within the same candidate
allowlist; no side effects or LLM calls occur here.
"""
from __future__ import annotations

from praxis_virtualcell.biological_modules import module_gene_sets

_M2 = "genetic_hub"
_M3 = "mitochondrial_energy_metabolism"
_M4 = "cytoplasmic_metabolism"
_M6 = "cytoskeletal_framework"
_M7 = "stress_processor"
_M8 = "degradation_machinery"

_METABOLIC = {"growth", "flux"}
_GENE_LIKE = {"gene", "gene_combination"}


def pick_primary(req: dict) -> str:
    """Deterministically map (perturbation_object, target_output) to the primary module."""
    obj = req["perturbation_object"]
    out = req["target_output"]
    if out in _METABOLIC:
        return _M4
    if out == "expression":
        if obj in _GENE_LIKE:
            return _M2
        return _M7
    if out == "state":
        if obj == "medium" and str(req.get("medium", "")).lower() == "niche":
            return _M6
        return _M7
    if out == "communication":
        return _M7
    return _M7


def gene_set_secondary(req: dict) -> list[str]:
    """Return gene-set matches among advisory modules M1/M5/M8 in MODULE_ORDER. Activate only gene/gene_combination
    perturbations; drug/ligand names cannot activate gene advisories by accidental symbol matches. Return an
    empty list for other objects or no matches.
    """
    if req["perturbation_object"] not in _GENE_LIKE:
        return []
    return module_gene_sets.modules_hit_by(req.get("perturbation_targets", []))


def pick_secondary(req: dict, primary: str) -> list[str]:
    """Choose a minimal deterministic secondary set. Mammalian growth/flux includes M3; gene-set matches add
    advisory M1/M5/M8. Advisory modules produce no delta, and prediction authority remains with the
    request-level engine.
    """
    out = req["target_output"]
    species = req["species"]
    sec: list[str] = []
    if out in _METABOLIC and species in ("human", "mouse"):
        sec.append(_M3)

    sec += gene_set_secondary(req)

    result: list[str] = []
    for m in sec:
        if m != primary and m not in result:
            result.append(m)
    return result


def mismatch_query_for(req: dict, module: str) -> str | None:
    """Derive a biological_mismatch query from (species, module); the registry supplies its verdict."""
    species = req["species"]
    if species == "bacteria" and module == _M8:
        return "bacteria_autophagy"
    if species == "yeast" and module == _M6:
        return "tissue_spatial_niche"
    return None

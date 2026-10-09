"""Deterministically map request perturbation_type, output_modality, and metadata.requested_outputs to
module-routing perturbation_object, target_output, and perturbation_targets. Shared by runtime,
ModelApplicability, and CaseRunner; no LLM is used.
"""
from __future__ import annotations

_OUT_MAP = {"delta_expression": "expression", "pathway_response": "flux",
            "reliability_report": "expression", "growth": "growth", "flux": "flux",
            "state": "state", "communication": "communication", "expression": "expression"}


def request_to_module_input(req: dict) -> dict:
    requested = ((req.get("metadata") or {}).get("requested_outputs") or [])
    target_output = next((o for o in requested if o in _OUT_MAP.values()), None)
    if target_output is None:
        target_output = _OUT_MAP.get(str(req.get("output_modality", "")).lower(), "expression")
    raw = {"species": req.get("species"),
           "perturbation_object": req.get("perturbation_type"),
           "target_output": target_output,
           "perturbation_targets": list(req.get("perturbation_targets") or [])}
    for k in ("cell_type", "medium", "dose", "perturbation_dose"):
        if req.get(k) is not None:
            raw[k] = req[k]
    return raw

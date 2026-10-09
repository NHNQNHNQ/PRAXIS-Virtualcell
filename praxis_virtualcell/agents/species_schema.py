"""Species-aware request validation and object normalization. Objects: gene/gene_combination/drug/medium/ligand;
readouts: expression/growth/flux/state/communication. This layer predicts nothing. Invalid or missing fields
raise SchemaError without silently adding defaults; downstream models execute after routing.
"""
from __future__ import annotations

SPECIES = {"human", "mouse", "yeast", "bacteria"}


PERTURBATION_OBJECTS = {"gene", "gene_combination", "drug", "medium", "ligand"}


TARGET_OUTPUTS = {"expression", "growth", "flux", "state", "communication"}


_GENE_LIKE = {"gene", "gene_combination"}


class SchemaError(ValueError):
    """Request schema violation: unknown vocabulary, missing fields, or empty targets."""


def _norm_target(obj: str, t: str) -> str:
    """Normalize a target identifier according to its perturbation object."""
    s = str(t).strip()
    if obj in _GENE_LIKE or obj == "ligand":
        return s.upper()
    if obj == "drug":
        return s.lower()
    return s


def normalize_request(raw: dict) -> dict:
    """Validate and normalize a request dictionary. Required: species, perturbation_object, target_output.
    Gene/gene_combination/drug/ligand require nonempty perturbation_targets; medium is exempt. Optional
    cell_type, medium, and dose are passed through with whitespace stripped.
    """
    if not isinstance(raw, dict):
        raise SchemaError(f"request must be a dict; received {type(raw).__name__}")

    species = str(raw.get("species", "")).strip().lower()
    obj = str(raw.get("perturbation_object", "")).strip().lower()
    out = str(raw.get("target_output", "")).strip().lower()

    if species not in SPECIES:
        raise SchemaError(f"unknown species={species!r}(supported:{sorted(SPECIES)})")
    if obj not in PERTURBATION_OBJECTS:
        raise SchemaError(f"unknown perturbation_object={obj!r}(supported:{sorted(PERTURBATION_OBJECTS)})")
    if out not in TARGET_OUTPUTS:
        raise SchemaError(f"unknown target_output={out!r}(supported:{sorted(TARGET_OUTPUTS)})")

    targets_raw = raw.get("perturbation_targets")
    if obj != "medium":
        if not targets_raw:
            raise SchemaError(f"perturbation_object={obj} requires nonempty perturbation_targets")
        targets = [_norm_target(obj, t) for t in targets_raw]
    else:
        targets = [_norm_target(obj, t) for t in (targets_raw or [])]

    req: dict = {
        "species": species,
        "perturbation_object": obj,
        "target_output": out,
        "perturbation_targets": targets,
    }

    for k in ("cell_type", "medium", "dose"):
        if raw.get(k) is not None:
            req[k] = str(raw[k]).strip()
    return req

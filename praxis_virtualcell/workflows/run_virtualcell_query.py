"""Shared natural-language query service for CLI, API, and web clients.

Candidates are parsed, validated, and confirmed before deterministic execution.
LLMs may interpret requests, suggest routes, critique, and narrate results.
Predictions, governance verdicts, and provenance remain runtime decisions.
Offline mode makes no LLM calls.
"""

from __future__ import annotations

import hashlib
import json
import math
import re

from praxis_virtualcell.core.config import RuntimeConfig, assert_llm_boundaries
from praxis_virtualcell.core.request import VirtualCellRequest

SUPPORTED_SPECIES = {"human", "mouse", "yeast", "bacteria"}
SUPPORTED_PERTURBATION = {"gene", "gene_combination", "drug", "medium", "ligand"}
SUPPORTED_TASKS = {"predict_delta_expression"}
ALLOWED_OUTPUTS = {
    "delta_expression",
    "pathway_response",
    "reliability_report",
    "growth",
    "flux",
    "state",
    "communication",
}
_REQUIRED = ("species", "perturbation_type", "perturbation_targets", "task_type")
_STRUCTURED_DESCRIPTION_MARKER = "Structured description:"
_STRUCTURED_FIELDS = frozenset(
    {
        "species",
        "cell_type",
        "perturbation_type",
        "perturbation_targets",
        "input_modality",
        "output_modality",
        "task_type",
        "requested_outputs",
    }
)
_STRUCTURED_MARKER_RE = re.compile(rf"(?m)^{re.escape(_STRUCTURED_DESCRIPTION_MARKER)}")

_LLM_SYS = (
    "Parse the user's virtual-cell experiment into JSON. Return JSON only, without explanation. "
    "Fields: species (lowercase human/mouse/yeast/bacteria), cell_type, "
    "perturbation_type (gene/gene_combination/drug/medium/ligand), perturbation_targets (array), "
    "task_type (predict_delta_expression), requested_outputs (array), confidence (0-1), "
    "missing_fields (array), assumptions (array). Leave unknown fields empty or omit them."
)


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _is_utf8_safe(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _response_safe_candidate(cand: dict) -> dict:
    """Keep response-safe invalid candidates available for correction; otherwise return an empty shell."""
    if not _is_json_response_safe(cand):
        return {"perturbation_targets": []}
    return cand


def _within_response_budget(value, *, max_depth: int = 64, max_nodes: int = 4096) -> bool:
    """Iterative structure budget keeps framework serializers away from depth overflows."""
    stack = [(value, 0)]
    seen_nodes = 0
    while stack:
        current, depth = stack.pop()
        seen_nodes += 1
        if depth > max_depth or seen_nodes > max_nodes:
            return False
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend((item, depth + 1) for item in current)
    return True


def _is_json_response_safe(value) -> bool:
    if not _within_response_budget(value):
        return False
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        return False
    return len(encoded) <= 262_144


def _safe_text_list(value) -> list[str]:
    return [item for item in value if isinstance(item, str) and _is_utf8_safe(item)] if isinstance(value, list) else []


def _safe_llm_error(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and _is_utf8_safe(value):
        return value
    return "llm_error_not_response_safe"


def _safe_parse_failure(error: str = "parse_response_not_json_safe") -> dict:
    return {
        "candidate_request": {"perturbation_targets": []},
        "schema_valid": False,
        "missing_fields": [],
        "errors": [error],
        "clarification_required": True,
        "parser": "deterministic",
        "llm_used": False,
        "fallback_used": True,
        "assumptions": [],
        "llm_metadata": {},
    }


def _extract_structured_description(text: str) -> tuple[str, dict | None, list[str]]:
    """Extract an explicit JSON request overlay, rejecting unknown fields and malformed values."""
    matches = list(_STRUCTURED_MARKER_RE.finditer(text))
    if not matches:
        return text, None, []
    marker = matches[-1]
    natural_text = text[: marker.start()].rstrip()
    raw = text[marker.end() :].strip()
    if not raw:
        return natural_text, None, ["structured_description_malformed"]
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError, RecursionError):
        return natural_text, None, ["structured_description_malformed"]
    if not isinstance(parsed, dict):
        return natural_text, None, ["structured_description_not_object"]
    errors = ["structured_description_unknown_fields"] if set(parsed) - _STRUCTURED_FIELDS else []
    if "requested_outputs" in parsed:
        requested_outputs = parsed["requested_outputs"]
        if not isinstance(requested_outputs, list) or not all(isinstance(item, str) for item in requested_outputs):
            errors.append("invalid_requested_outputs_type")
        elif any(item not in ALLOWED_OUTPUTS for item in requested_outputs):
            errors.append("unsupported_requested_outputs")
    if "perturbation_targets" in parsed and (
        not isinstance(parsed["perturbation_targets"], list)
        or not all(isinstance(item, str) for item in parsed["perturbation_targets"])
    ):
        errors.append("invalid_perturbation_targets_type")
    overlay = {key: parsed[key] for key in _STRUCTURED_FIELDS if key in parsed}
    return natural_text, overlay, errors


def coerce_str_list(value) -> list[str]:
    """Read untrusted candidate values as a list of strings.

Reject non-list containers to avoid splitting strings into characters, then
filter non-string elements. This guard applies even to invalid candidates
returned for user correction.
    """
    return _safe_text_list(value)


def validate_candidate(cand: dict) -> dict:
    """Validate and normalize a candidate deterministically.

Return schema validity, missing fields, errors, and a normalized request.
Malformed Python values that raise TypeError, AttributeError, ValueError,
or RecursionError produce candidate_malformed. Process-control and other
unexpected exceptions are not suppressed.
    """
    try:
        return _validate_candidate_impl(cand)
    except (TypeError, AttributeError, ValueError, RecursionError):
        return {"schema_valid": False, "missing_fields": [], "errors": ["candidate_malformed"], "normalized": None}


def _validate_candidate_impl(cand: dict) -> dict:
    """Implement normalization inside the public validator exception boundary."""
    errors, missing = [], []
    d = dict(cand or {})
    serialized = json.dumps(d, sort_keys=True, ensure_ascii=False)
    try:
        serialized.encode("utf-8")
    except UnicodeEncodeError:
        return {"schema_valid": False, "missing_fields": [], "errors": ["candidate_not_utf8_safe"], "normalized": None}
    species = str(d.get("species", "")).strip().lower()


    _perturbation = d.get("perturbation")
    _perturbation = _perturbation if isinstance(_perturbation, dict) else {}
    ptype = str(d.get("perturbation_type") or _perturbation.get("type", "")).strip().lower()
    targets = d.get("perturbation_targets")
    if targets is None and _perturbation:
        targets = _perturbation.get("targets")


    targets = [t.strip() for t in targets if isinstance(t, str) and t.strip()] if isinstance(targets, list) else []
    task = str(d.get("task_type") or d.get("task", "")).strip().lower() or "predict_delta_expression"
    raw_output_modality = d.get("output_modality")
    if raw_output_modality in (None, ""):
        output_modality = "delta_expression"
    elif isinstance(raw_output_modality, str):
        output_modality = raw_output_modality.strip().lower()
        if output_modality not in ALLOWED_OUTPUTS:
            errors.append(f"unsupported_output_modality:{output_modality}")
    else:
        output_modality = ""
        errors.append("invalid_output_modality_type")
    raw_input_modality = d.get("input_modality")
    if raw_input_modality in (None, ""):
        input_modality = "scRNA"
    elif isinstance(raw_input_modality, str):
        input_modality = raw_input_modality.strip()
    else:
        input_modality = ""
        errors.append("invalid_input_modality_type")
    raw_cell_type = d.get("cell_type")
    if raw_cell_type is None:
        cell_type = None
    elif isinstance(raw_cell_type, str):
        cell_type = raw_cell_type.strip() or None
    else:
        cell_type = None
        errors.append("invalid_cell_type_type")
    raw_request_id = d.get("request_id")
    if raw_request_id in (None, ""):
        request_id = "vc-" + _hash(serialized)
    elif isinstance(raw_request_id, str) and raw_request_id.strip():
        request_id = raw_request_id.strip()
    else:
        request_id = ""
        errors.append("invalid_request_id_type")
    raw_metadata = d.get("metadata")
    if raw_metadata is None:
        metadata = {}
    elif isinstance(raw_metadata, dict):
        metadata = dict(raw_metadata)
        if not _is_json_response_safe(metadata):
            errors.append("invalid_metadata_value")
            metadata = {}
    else:
        errors.append("invalid_metadata_type")
        metadata = {}
    _raw_outputs = d.get("requested_outputs") if "requested_outputs" in d else metadata.get("requested_outputs")


    outputs = (
        [o for o in _raw_outputs if isinstance(o, str) and o in ALLOWED_OUTPUTS]
        if isinstance(_raw_outputs, list)
        else []
    )

    _raw_assumptions = d.get("assumptions") if "assumptions" in d else metadata.get("assumptions")
    assumptions = _safe_text_list(_raw_assumptions)
    metadata["requested_outputs"] = outputs
    metadata["assumptions"] = assumptions

    raw_tissue = d.get("tissue")
    if raw_tissue is None:
        tissue = None
    elif isinstance(raw_tissue, str):
        tissue = raw_tissue.strip() or None
    else:
        tissue = None
        errors.append("invalid_tissue_type")
    raw_perturbation_time = d.get("perturbation_time")
    if raw_perturbation_time is None:
        perturbation_time = None
    elif isinstance(raw_perturbation_time, str):
        perturbation_time = raw_perturbation_time.strip() or None
    else:
        perturbation_time = None
        errors.append("invalid_perturbation_time_type")
    raw_dose = d.get("perturbation_dose")
    if raw_dose is None:
        perturbation_dose = None
    else:
        perturbation_dose = None
        if isinstance(raw_dose, (int, float)) and not isinstance(raw_dose, bool):
            try:
                normalized_dose = float(raw_dose)
            except (OverflowError, TypeError, ValueError):
                normalized_dose = math.nan
            if math.isfinite(normalized_dose):
                perturbation_dose = normalized_dose
        if perturbation_dose is None:
            errors.append("invalid_perturbation_dose")
    raw_baseline = d.get("baseline_context")
    if raw_baseline is None:
        baseline_context = raw_baseline
    elif isinstance(raw_baseline, dict) and _is_json_response_safe(raw_baseline):
        baseline_context = raw_baseline
    else:
        baseline_context = None
        errors.append("invalid_baseline_context")
    raw_constraints = d.get("constraints")
    if raw_constraints is None:
        constraints = {}
    elif isinstance(raw_constraints, dict) and _is_json_response_safe(raw_constraints):
        constraints = raw_constraints
    else:
        constraints = {}
        errors.append("invalid_constraints")

    if not species:
        missing.append("species")
    elif species not in SUPPORTED_SPECIES:
        errors.append(f"unsupported_species:{species}")
    if not ptype:
        missing.append("perturbation_type")
    elif ptype not in SUPPORTED_PERTURBATION:
        errors.append(f"unsupported_perturbation_type:{ptype}")
    if ptype != "medium" and not targets:
        missing.append("perturbation_targets")
    if task not in SUPPORTED_TASKS:
        errors.append(f"unsupported_task:{task}")


    if ptype in ("gene", "gene_combination", "ligand"):
        targets = [t.upper() for t in targets]
    elif ptype == "drug":
        targets = [t.lower() for t in targets]

    normalized = {
        "request_id": request_id,
        "species": species,
        "perturbation_type": ptype,
        "perturbation_targets": targets,
        "input_modality": input_modality,
        "output_modality": output_modality,
        "task_type": task,
        "cell_type": cell_type,
        "tissue": tissue,
        "perturbation_dose": perturbation_dose,
        "perturbation_time": perturbation_time,
        "baseline_context": baseline_context,
        "metadata": metadata,
        "constraints": constraints,
    }
    schema_valid = not missing and not errors
    return {
        "schema_valid": schema_valid,
        "missing_fields": missing,
        "errors": errors,
        "normalized": normalized if schema_valid else None,
    }


def _deterministic_parse(text: str) -> dict:
    """Extract explicit species and target signals without an LLM."""
    t = text.lower()
    species = next((s for s in ("human", "mouse", "yeast", "bacteria") if s in t), "")
    for alias, canonical in (("e. coli", "bacteria"), ("e.coli", "bacteria")):
        if not species and alias in t:
            species = canonical
    ptype = "drug" if "drug" in t else "gene"

    genes = re.findall(r"\b[A-Z][A-Z0-9]{1,7}\b", text)
    genes = [g for g in genes if g not in ("K562", "T", "DNA", "RNA", "AND", "OR")][:4]
    return {
        "species": species,
        "perturbation_type": ptype,
        "perturbation_targets": genes,
        "task_type": "predict_delta_expression",
        "assumptions": ["deterministic keyword parse"],
    }


def parse_query(text: str, *, config: RuntimeConfig | None = None) -> dict:
    """Parse natural language into a candidate, validation results, and parser metadata."""
    cfg = config or RuntimeConfig.from_env()
    assert_llm_boundaries(cfg)
    if not _is_utf8_safe(text):
        return {
            "candidate_request": {"perturbation_targets": []},
            "schema_valid": False,
            "missing_fields": [],
            "errors": ["query_not_utf8_safe"],
            "clarification_required": True,
            "parser": "deterministic",
            "llm_used": False,
            "fallback_used": True,
            "assumptions": [],
            "llm_metadata": {},
        }

    natural_text, structured_overlay, structured_errors = _extract_structured_description(text)
    llm_used = fallback_used = False
    llm_metadata: dict = {}
    cand = None
    assumptions: list = []
    if cfg.llm_enabled:
        from praxis_virtualcell.agents_llm.llm_client import make_llm_client

        client = make_llm_client(cfg)
        res = client.complete(
            [{"role": "system", "content": _LLM_SYS}, {"role": "user", "content": natural_text}], json_mode=True
        )
        content = res.get("content")
        content_is_safe = isinstance(content, str) and _is_utf8_safe(content)
        safe_model = (
            cfg.deepseek_model
            if isinstance(cfg.deepseek_model, str) and _is_utf8_safe(cfg.deepseek_model)
            else "unknown"
        )
        llm_metadata = {
            "provider": "deepseek",
            "model": safe_model,
            "prompt_hash": _hash(_LLM_SYS + natural_text),
            "response_hash": _hash(content) if content and content_is_safe else None,
            "error": _safe_llm_error(res.get("error")),
            "schema_valid": None,
            "fallback_used": False,
        }
        if content and content_is_safe:
            try:
                cand = json.loads(content)


                raw_assumptions = cand.get("assumptions")
                llm_used = True


                assumptions = _safe_text_list(raw_assumptions)


            except (json.JSONDecodeError, TypeError, AttributeError, RecursionError):
                cand = None
        elif content:
            llm_metadata["error"] = "response_not_utf8_safe"
    if cand is None:
        cand = _deterministic_parse(natural_text)
        fallback_used = True
        assumptions = coerce_str_list(cand.get("assumptions"))
    else:
        cand = dict(cand)

        cand.pop("request_id", None)
    if structured_overlay is not None:
        cand = {**cand, **structured_overlay}

    v = validate_candidate(cand)
    errors = [*structured_errors, *v["errors"]]
    schema_valid = v["schema_valid"] and not structured_errors
    if llm_metadata:
        llm_metadata["schema_valid"] = schema_valid
        llm_metadata["fallback_used"] = fallback_used
    raw_candidate = {**cand, "perturbation_targets": cand.get("perturbation_targets", [])}
    result = {
        "candidate_request": v["normalized"] or _response_safe_candidate(raw_candidate),
        "schema_valid": schema_valid,
        "missing_fields": v["missing_fields"],
        "errors": errors,
        "clarification_required": not schema_valid,
        "parser": "llm_with_validator" if llm_used else "deterministic",
        "llm_used": llm_used,
        "fallback_used": fallback_used,
        "assumptions": assumptions,
        "llm_metadata": llm_metadata,
    }
    return result if _is_json_response_safe(result) else _safe_parse_failure()


def run_query(
    request_dict: dict,
    *,
    config: RuntimeConfig | None = None,
    enable_llm_report: bool = False,
    pack_id: str | None = None,
    pack_version: str | None = None,
    pack_registry=None,
    model_registry=None,
    model_cache=None,
    environment=None,
    _include_legacy_predictors: bool = True,
) -> dict:
    """Compatibility query harness; formal product callers use ``run_formal_query``."""
    cfg = config or RuntimeConfig.from_env()
    assert_llm_boundaries(cfg)
    from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

    rt = build_runtime(
        cfg,
        model_registry=model_registry,
        model_cache=model_cache,
        pack_registry=pack_registry,
        environment=environment,
        include_legacy_predictors=_include_legacy_predictors,
    )
    req = dict(request_dict)
    if not req.get("request_id"):
        req["request_id"] = "vc-" + _hash(json.dumps(req, sort_keys=True, ensure_ascii=False))
    report = rt.run_workflow(
        VirtualCellRequest.from_dict(req),
        pack_id=pack_id,
        pack_version=pack_version,
    )
    _tr = getattr(rt.bus, "trace", None)
    _msgs = _tr() if callable(_tr) else (_tr if isinstance(_tr, list) else getattr(rt.bus, "_trace", []))
    trace = [
        {
            "message_id": m.message_id,
            "sender": m.sender,
            "receiver": m.receiver,
            "message_type": m.message_type,
            "timestamp": m.timestamp,
            "schema_version": m.schema_version,
            "trace_id": m.trace_id,
            "task_id": m.task_id,
        }
        for m in _msgs
    ]
    return {
        "structured_report": {k: v for k, v in report.items() if k != "narrative"},
        "narrative": report.get("narrative"),
        "trace": trace,
        "provenance": report.get("provenance", {}),
        "reliability_decision": {
            "abstain": report.get("abstain"),
            "reliability": report.get("reliability"),
            "learned_reliability": report.get("learned_reliability"),
        },
        "llm_used_for_prediction": False,
        "mode": cfg.mode.value,
        "llm_enabled": cfg.llm_enabled,
    }


def run_formal_query(
    request_dict: dict,
    *,
    config: RuntimeConfig | None = None,
    enable_llm_report: bool = False,
    pack_id: str | None = None,
    pack_version: str | None = None,
    pack_registry=None,
    model_registry=None,
    model_cache=None,
    environment=None,
) -> dict:
    """Formal product entry: unbound requests abstain; legacy predictors stay absent."""
    return run_query(
        request_dict,
        config=config,
        enable_llm_report=enable_llm_report,
        pack_id=pack_id,
        pack_version=pack_version,
        pack_registry=pack_registry,
        model_registry=model_registry,
        model_cache=model_cache,
        environment=environment,
        _include_legacy_predictors=False,
    )


def run_full_query(text: str, *, config: RuntimeConfig | None = None, enable_llm_report: bool = False) -> dict:
    """Parse and run valid requests; confirmation UIs use the separate parse and run functions."""
    parsed = parse_query(text, config=config)
    if not parsed["schema_valid"]:
        return {"stage": "clarification_required", **parsed}
    out = run_formal_query(
        parsed["candidate_request"],
        config=config,
        enable_llm_report=enable_llm_report,
    )
    return {"stage": "done", "parsed": parsed, **out}

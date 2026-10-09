"""Score frozen Qwen predictions after inference; labels never enter generation.

Repeated measurements are empirical targets, not calibrated distributions. Exact
observation lists are compared in log2 space after sorting (order independent).
Censored observations retain their relation and bounds; they are not imputed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
import json
import math
from pathlib import Path

from praxis_virtualcell.llm_prediction.schemas import Assessment, MICObservation
from .labels import ExperimentRecord
from .paths import dataset_file
from .species_registry import _digest
from .strain_dataset import _normalize

FIELDS = ("relation", "value", "lower", "upper", "lower_closed", "upper_closed")


def _strain_matches(native: ExperimentRecord, organism: dict) -> bool:
    """Use the same label normalization as the frozen public strain inputs.

    native_strain_label preserves source wording such as "isolate RUH134";
    organism.strain is the curated identity that the public label was built from.
    A study-local spelling also requires its original source namespace.
    """
    label = _normalize(native.organism.strain)
    if label is None or label != _normalize(organism.get("label")):
        return False
    namespace = organism.get("namespace")
    if isinstance(namespace, str) and namespace.startswith("study:"):
        allowed = {"study:" + value for value in
                   (native.source.document_id, native.source.doi, native.source.source_id) if value}
        return namespace in allowed
    return True


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _contains(observation: dict, value: float) -> bool:
    lower, upper = observation["lower"], observation["upper"]
    return ((lower is None or value > lower or value == lower and observation["lower_closed"])
            and (upper is None or value < upper or value == upper and observation["upper_closed"]))


def _prediction(row: dict) -> tuple[dict | None, str | None]:
    if row.get("status") not in {None, "completed"}:
        return None, row.get("status", "failed")
    target = row.get("assessment", row.get("response"))
    if isinstance(target, str):
        try:
            target = json.loads(target)
        except (ValueError, TypeError):
            return None, "invalid_json"
    if not isinstance(target, dict):
        return None, "missing_assessment"
    try:
        if "mic_estimate" in target:
            target = deepcopy(target)
            for item in target.get("targets", []):
                if not isinstance(item, dict):
                    raise ValueError("invalid_target_hypothesis")
                if "causality_verified" in item and item["causality_verified"] is not False:
                    raise ValueError("unverified_target_causality")
                if "identity_observed" in item and item["identity_observed"] is not (item.get("target_id") is not None):
                    raise ValueError("target_identity_display_flag_mismatch")
                item.pop("causality_verified", None)
                item.pop("identity_observed", None)
            for item in target.get("mechanism_hypotheses", []):
                if not isinstance(item, dict):
                    raise ValueError("invalid_mechanism_hypothesis")
                if "causality_verified" in item and item["causality_verified"] is not False:
                    raise ValueError("unverified_mechanism_causality")
                item.pop("causality_verified", None)
            return Assessment.model_validate(target).model_dump(), None
        # Old numeric exports remain scoreable for comparison, with the same
        # strict relation validation as new reports.
        if target.get("endpoint") != "MIC" or target.get("unit") != "ug/mL":
            raise ValueError("MIC_unit_or_endpoint")
        observations = [MICObservation.model_validate(item).model_dump() for item in target["observations"]]
        value = (observations[0]["value"] if observations and all(
            item["relation"] == "=" and item["value"] == observations[0]["value"] for item in observations) else None)
        return {"mic_observations": observations, "mic_estimate": {"value": value}}, None
    except (ValueError, KeyError, TypeError):
        return None, "invalid_assessment_contract"


def _metrics(cases: list[dict]) -> dict:
    completed = [row for row in cases if row["error"] is None]
    errors = [error for row in cases for error in row["point_errors_log2"]]
    consistency = [value for row in cases for value in row["censored_point_consistency"]]
    return {
        "record_count": len(cases), "valid_report_count": len(completed),
        "report_coverage": len(completed) / len(cases) if cases else None,
        "point_prediction_count": sum(row["point_predicted"] for row in cases),
        "point_coverage": _mean([float(row["point_predicted"]) for row in cases]),
        "point_exact_measurements_scored": len(errors), "point_mae_log2": _mean(errors),
        "point_within_one_dilution": _mean([float(error <= 1) for error in errors]),
        "point_within_two_dilutions": _mean([float(error <= 2) for error in errors]),
        "censored_point_measurements_scored": len(consistency),
        "censored_point_consistency": _mean([float(value) for value in consistency]),
        "observation_count_match_rate": _mean([float(row["observation_count_match"]) for row in completed]),
        "observation_relation_multiset_match_rate": _mean([float(row["relation_match"]) for row in completed]),
        "exact_observation_list_records_scored": sum(row["exact_list_mae_log2"] is not None for row in cases),
        "exact_observation_list_mae_log2": _mean([row["exact_list_mae_log2"] for row in cases
                                                 if row["exact_list_mae_log2"] is not None]),
        "censored_boundary_records_scored": sum(row["censored_boundary_mae_log2"] is not None for row in cases),
        "censored_boundary_mae_log2": _mean([row["censored_boundary_mae_log2"] for row in cases
                                             if row["censored_boundary_mae_log2"] is not None]),
        "invalid_or_failed_records": dict(Counter(row["error"] for row in cases if row["error"])),
    }


def _case_metrics(record_id: str, target: dict | None, error: str | None,
                  truth: list[dict], cohorts: list[str], species: str, strain: str | None) -> dict:
    point = target["mic_estimate"]["value"] if target else None
    predicted = target.get("mic_observations", []) if target else []
    exact = [row["value"] for row in truth if row["relation"] == "="]
    prediction_exact = [row["value"] for row in predicted if row["relation"] == "="]
    same_count = len(predicted) == len(truth)
    relation_match = Counter(row["relation"] for row in predicted) == Counter(row["relation"] for row in truth)
    exact_distance = None
    if same_count and len(exact) == len(truth) and len(prediction_exact) == len(predicted) and exact:
        exact_distance = _mean([abs(math.log2(a / b)) for a, b in zip(sorted(prediction_exact), sorted(exact), strict=True)])
    censored_distance = None
    if same_count and relation_match:
        errors = []
        for relation in ("<", "<=", ">", ">=", "interval"):
            actual = sorted((row for row in truth if row["relation"] == relation),
                            key=lambda row: (row["lower"] or 0, row["upper"] or float("inf")))
            estimates = sorted((row for row in predicted if row["relation"] == relation),
                               key=lambda row: (row["lower"] or 0, row["upper"] or float("inf")))
            for a, b in zip(actual, estimates, strict=True):
                for boundary in ("lower", "upper"):
                    if a[boundary] is not None and b[boundary] is not None:
                        errors.append(abs(math.log2(a[boundary] / b[boundary])))
        censored_distance = _mean(errors)
    return {"record_id": record_id, "cohorts": cohorts, "species": species, "strain": strain,
            "error": error, "point_predicted": point is not None,
            "point_errors_log2": [abs(math.log2(point / value)) for value in exact] if point else [],
            "censored_point_consistency": [_contains(row, point) for row in truth if row["relation"] != "="] if point else [],
            "observation_count_match": same_count, "relation_match": relation_match,
            "exact_list_mae_log2": exact_distance, "censored_boundary_mae_log2": censored_distance}


def score_qwen_predictions(dataset_dir: str | Path, predictions: str | Path, *, split: str = "validation",
                           source_path_map: dict[str, str] | str | Path | None = None,
                           audit_path: str | Path | None = None, allow_unaudited: bool = False,
                           pilot_subset: bool = False) -> dict:
    """Private answer locators are opened here, only after predictions exist."""
    if split not in {"validation", "test"}:
        raise ValueError("heldout_split_required")
    root = Path(dataset_dir)
    manifest = json.loads((root / "manifest.json").read_text())
    for name in (f"{split}.inputs.jsonl", f"{split}.answers.index.jsonl"):
        if _digest(dataset_file(root, name, manifest)) != manifest["files"][name]["sha256"]:
            raise ValueError("frozen_evaluation_file_changed")
    mapping = (source_path_map if isinstance(source_path_map, dict) else
               json.loads(Path(source_path_map).read_text()) if source_path_map else {})
    inputs = {row["record_id"]: row for row in _rows(root / f"{split}.inputs.jsonl")}
    answers = _rows(dataset_file(root, f"{split}.answers.index.jsonl", manifest))
    if len({row["record_id"] for row in answers}) != len(answers) or set(inputs) != {row["record_id"] for row in answers}:
        raise ValueError("frozen_answer_input_identity_mismatch")
    supplied = _rows(Path(predictions))
    predicted = {row["record_id"]: row for row in supplied}
    if len(predicted) != len(supplied) or set(predicted) - set(inputs):
        raise ValueError("duplicate_or_unknown_prediction_record")
    if pilot_subset and not predicted:
        raise ValueError("pilot_subset_requires_predictions")
    audit = json.loads(Path(audit_path).read_text()) if audit_path else {}
    audit_valid = (audit.get("status") == "reviewed" and audit.get("split") == split
                   and audit.get("dataset_manifest_sha256") == _digest(root / "manifest.json"))
    if not audit_valid and not allow_unaudited:
        raise ValueError("native_assay_review_required_for_formal_scoring")
    # An audit for another snapshot/split has no authority over this cohort,
    # even when the caller explicitly permits preliminary unaudited scoring.
    excluded = set(audit.get("excluded_record_ids", [])) if audit_valid else set()
    if excluded - set(inputs):
        raise ValueError("assay_audit_contains_unknown_record")
    cases = []
    with ExitStack() as stack:
        streams, verified_digests = {}, {}
        for answer in answers:
            record_id = answer["record_id"]
            if record_id in excluded or pilot_subset and record_id not in predicted:
                continue
            public = inputs[record_id]
            request = json.loads(next(message["content"] for message in public["messages"] if message["role"] == "user"))
            target, error = _prediction(predicted[record_id]) if record_id in predicted else (None, "missing_prediction")
            observations = []
            for source in answer["private_answer_refs"]:
                locator = source["locator"]
                path = Path(mapping.get(locator["path"], locator["path"]))
                if path not in streams:
                    verified_digests[path] = _digest(path)
                    streams[path] = stack.enter_context(path.open("rb"))
                if verified_digests[path] != locator["sha256"]:
                    raise ValueError("private_MIC_source_bytes_changed")
                stream = streams[path]
                stream.seek(locator["byte_offset"])
                native = ExperimentRecord.model_validate_json(stream.readline())
                if (native.record_id != locator["record_id"] or native.endpoint.kind != "MIC"
                        or native.endpoint.unit != "ug/mL" or not native.admission.label_eligible
                        or native.molecule.canonical_smiles != request["candidate"]["smiles"]
                        or native.organism.taxon_id != request["organism"]["taxon_id"]
                        or not _strain_matches(native, request["organism"])):
                    raise ValueError("private_MIC_locator_identity_mismatch")
                observations.append({key: getattr(native.endpoint, key) for key in FIELDS})
            cases.append(_case_metrics(record_id, target, error, observations, public.get("cohorts", []),
                                       request["organism"]["species"], request["organism"].get("label")))
    by_species = {species: _metrics([row for row in cases if row["species"] == species])
                  for species in sorted({row["species"] for row in cases})}
    report = {"schema_version": "praxis.qwen-evaluation.v1", "split": split,
              "status": "scored" if audit_valid else "preliminary_unaudited",
              "metrics_scope": "pilot_supplied_predictions_only" if pilot_subset else "full_frozen_split",
              "frozen_input_count": len(inputs), "supplied_prediction_count": len(predicted),
              "metrics": _metrics(cases), "by_species": by_species,
              "species_macro": {
                  "species_count": len(by_species),
                  "species_with_exact_point_scores": sum(value["point_mae_log2"] is not None for value in by_species.values()),
                  "point_mae_log2": _mean([value["point_mae_log2"] for value in by_species.values()
                                           if value["point_mae_log2"] is not None]),
                  "report_coverage": _mean([value["report_coverage"] for value in by_species.values()]),
              },
              "by_cohort": {cohort: _metrics([row for row in cases if cohort in row["cohorts"]])
                            for cohort in sorted({cohort for row in cases for cohort in row["cohorts"]})},
              "excluded_record_count": len(excluded), "heldout_mechanism_gold_count": 0,
              "mechanism_accuracy": None, "calibrated_distribution_score": None,
              "limitations": ["Observation lists are empirical, not calibrated predictive distributions.",
                              "MIC values are opened by the scorer after inference, never supplied to generation.",
                              "Mechanism accuracy requires independently reviewed heldout gold."], "cases": cases}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--split", choices=["validation", "test"], default="validation")
    parser.add_argument("--source-path-map")
    parser.add_argument("--audit")
    parser.add_argument("--allow-unaudited", action="store_true", help="Pilot only; output marked preliminary")
    parser.add_argument("--pilot-subset", action="store_true", help="Score only supplied rows; explicitly marked pilot")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    result = score_qwen_predictions(args.dataset_dir, args.predictions, split=args.split,
                                    source_path_map=args.source_path_map, audit_path=args.audit,
                                    allow_unaudited=args.allow_unaudited, pilot_subset=args.pilot_subset)
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Evaluate one frozen train-only additive candidate on reused Golden validation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import stat
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).parents[1]
_BASE_PROTOCOL = _ROOT / "data/golden/norman_2019/additive_train_only_protocol.json"
_VALIDATION_PROTOCOL = _ROOT / "data/golden/norman_2019/additive_train_only_validation_protocol.json"
_BUILDER = _ROOT / "scripts/build_golden_additive_train_only_candidate.py"
_TRUTH_VERIFIER = _ROOT / "scripts/evaluate_golden_gears_train_only_validation.py"
_GEARS_PROTOCOL = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"
_CANDIDATE_FILES = {
    "baseline.json",
    "candidate-record.json",
    "linear_coefficients.npy",
    "linear_intercept.npy",
}


class ValidationError(ValueError):
    """Fail-closed additive development-validation error."""


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValidationError(f"required module is unavailable: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _builder():
    return _load_module("golden_additive_builder_for_validation", _BUILDER)


def _truth_verifier():
    return _load_module("golden_gears_truth_verifier_for_additive", _TRUTH_VERIFIER)


def _strict_json(path: Path, builder) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_bytes(),
            object_pairs_hook=builder._reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValidationError("non-finite JSON")),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"expected a JSON object: {path.name}")
    return value


def _load_protocol(path: Path) -> tuple[dict[str, Any], dict[str, Any], Any]:
    builder = _builder()
    try:
        base = builder._load_protocol(_BASE_PROTOCOL)
    except Exception as exc:
        raise ValidationError("base additive protocol identity changed") from exc
    value = _strict_json(path, builder)
    if value.get("schema_version") != "praxis.golden-additive-train-only-validation-protocol.v1":
        raise ValidationError("unsupported validation protocol")
    identity = value.get("identity", {})
    copy = json.loads(builder._canonical_bytes(value))
    copy["identity"]["payload_sha256"] = None
    if not (
        identity.get("payload_hash_algorithm")
        == "sha256(canonical_json(protocol_with_identity.payload_sha256_set_to_null))"
        and identity.get("payload_sha256") == builder._fingerprint(copy)
        and identity.get("base_protocol_path") == "data/golden/norman_2019/additive_train_only_protocol.json"
        and identity.get("base_protocol_payload_sha256") == base["identity"]["payload_sha256"]
        and identity.get("evaluator_path") == "scripts/evaluate_golden_additive_train_only_validation.py"
        and identity.get("evaluator_sha256") == builder._sha256(Path(__file__))
    ):
        raise ValidationError("validation protocol identity changed")
    return value, base, builder


def _require_frozen(protocol: dict[str, Any]) -> None:
    if not (
        protocol.get("implementation_status") == "FROZEN_EXECUTABLE"
        and protocol.get("truth_bundle", {}).get("status") == "FROZEN"
        and protocol.get("candidate_artifact", {}).get("status") == "FROZEN"
    ):
        raise ValidationError("validation inputs are not frozen; evaluation is not executable")


def _verify_reuse_disclosure(protocol: dict[str, Any], builder) -> dict[str, Any]:
    reuse = protocol.get("validation_reuse", {})
    prior = reuse.get("prior_validation_result", {})
    reason = (
        "preexisting_test_report_accidentally_read_during_science_design_audit_but_not_used_for_candidate_selection"
    )
    if not (
        reuse.get("validation_evidence_class") == "exposed_reused_development_validation"
        and reuse.get("independent") is False
        and reuse.get("access_round") == 2
        and prior.get("path") == "reports/science/golden-gears-linux-a100-validation-result.json"
        and builder._file_record(_ROOT / prior["path"], single_link=True)
        == {key: prior.get(key) for key in ("size_bytes", "sha256")}
        and reuse.get("candidate_iteration_occurred_after_prior_validation_failure") is True
        and reuse.get("candidate_model_class_selected_after_prior_golden_validation_failure") is True
        and reuse.get("decision_path_is_adaptive_to_prior_golden_validation_failure") is True
        and reuse.get("candidate_hyperparameters_selected_from_golden_validation_values") is False
        and reuse.get("candidate_hyperparameter_selection_source")
        == "frozen_train_only_93_condition_fit_11_condition_internal_validation_only"
        and reuse.get("prospective_test_blinding") is False
        and reuse.get("prospective_test_blinding_reason") == reason
    ):
        raise ValidationError("validation reuse disclosure changed")
    return reuse


def _verify_runtime(protocol: dict[str, Any], base: dict[str, Any], builder) -> dict[str, Any]:
    expected = protocol["runtime"]
    try:
        gears_base = builder._load_base_protocol(base)
        runtime = builder._GEARS_TRAIN._verify_runtime(builder._GEARS_BUILDER, gears_base)
    except Exception as exc:
        raise ValidationError("frozen reduction runtime identity changed") from exc
    expected_probe = {
        "python": gears_base["runtime_environment"]["python"],
        "platform_system": gears_base["runtime_environment"]["platform_system"],
        "platform_machine": gears_base["runtime_environment"]["platform_machine"],
        "sysconfig_platform": gears_base["runtime_environment"]["sysconfig_platform"],
        "packages": gears_base["runtime_environment"]["packages"],
        "gears_source_manifest_sha256": gears_base["candidate"]["implementation"]["installed_source_manifest_sha256"],
    }
    if not (
        expected.get("source_base_protocol_payload_sha256") == gears_base["identity"]["payload_sha256"]
        and expected.get("source_builder_path") == "scripts/build_golden_gears_train_only_candidate.py"
        and expected.get("source_builder_sha256") == builder._sha256(_ROOT / expected["source_builder_path"])
        and expected.get("source_train_runner_path") == "scripts/train_golden_gears_train_only_candidate.py"
        and expected.get("source_train_runner_sha256") == builder._sha256(_ROOT / expected["source_train_runner_path"])
        and expected.get("source_runtime_environment_sha256") == builder._fingerprint(gears_base["runtime_environment"])
        and expected.get("expected_probe_sha256") == builder._fingerprint(expected_probe)
        and runtime == expected_probe
    ):
        raise ValidationError("frozen reduction runtime receipt changed")
    return {
        "source_runtime_environment_sha256": expected["source_runtime_environment_sha256"],
        "runtime_probe_sha256": builder._fingerprint(runtime),
        "runtime_probe": runtime,
    }


def _regular_inventory(root: Path) -> set[str]:
    if root.is_symlink() or not root.is_dir():
        raise ValidationError("artifact root must be a regular directory")
    files: set[str] = set()
    for path in root.rglob("*"):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValidationError("artifact inventory contains an unsafe entry")
        if stat.S_ISREG(info.st_mode):
            if info.st_nlink != 1:
                raise ValidationError("artifact inventory contains a linked file")
            files.add(path.relative_to(root).as_posix())
    return files


def _verify_truth_bundle(root: Path, protocol: dict[str, Any], builder):
    expected = protocol["truth_bundle"]
    verifier = _truth_verifier()
    gears_builder = verifier._builder()
    try:
        gears_base = gears_builder._load_protocol(_GEARS_PROTOCOL)
    except Exception as exc:
        raise ValidationError("truth source protocol identity changed") from exc
    if not (
        expected.get("source_base_protocol_path") == "data/golden/norman_2019/gears_train_only_protocol.json"
        and expected.get("source_base_protocol_payload_sha256") == gears_base["identity"]["payload_sha256"]
        and expected.get("verifier_path") == "scripts/evaluate_golden_gears_train_only_validation.py"
        and expected.get("verifier_sha256") == builder._sha256(_TRUTH_VERIFIER)
    ):
        raise ValidationError("truth verifier identity changed")
    try:
        metadata, truth = verifier._verify_truth_bundle(root, protocol, gears_base, gears_builder)
    except Exception as exc:
        raise ValidationError("validation truth bundle identity changed") from exc
    return metadata, truth


def _array(root: Path, name: str, record: dict[str, Any], builder) -> np.ndarray:
    path = root / name
    if record.get("filename") != name or builder._file_record(path, single_link=True) != {
        key: record[key] for key in ("size_bytes", "sha256")
    }:
        raise ValidationError(f"candidate array identity changed: {name}")
    try:
        value = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise ValidationError(f"candidate array is invalid: {name}") from exc
    if (
        list(value.shape) != record.get("shape")
        or str(value.dtype) != record.get("dtype")
        or value.dtype.str != "<f8"
        or not np.isfinite(value).all()
    ):
        raise ValidationError(f"candidate array contract changed: {name}")
    return np.asarray(value, dtype=np.float64)


def _verify_candidate(
    root: Path,
    protocol: dict[str, Any],
    base: dict[str, Any],
    builder,
    runtime: dict[str, Any],
):
    expected = protocol["candidate_artifact"]
    if _regular_inventory(root) != _CANDIDATE_FILES:
        raise ValidationError("candidate artifact inventory changed")
    files = expected.get("files")
    if not isinstance(files, dict) or set(files) != _CANDIDATE_FILES:
        raise ValidationError("frozen candidate file set is invalid")
    for name in sorted(_CANDIDATE_FILES):
        if builder._file_record(root / name, single_link=True) != files[name]:
            raise ValidationError(f"candidate artifact identity changed: {name}")

    record = _strict_json(root / "candidate-record.json", builder)
    baseline = _strict_json(root / "baseline.json", builder)
    selected_alpha = base["training"]["expected_selected_alpha"]
    source = base["train_only_source"]
    receipt_source = record.get("train_only_source", {})
    selection = record.get("internal_selection", {})
    final_refit = record.get("final_refit", {})
    if not (
        record.get("schema_version") == base["claim_ceiling"]["output_schema_version"]
        and record.get("record_role") == base["claim_ceiling"]["output_record_role"]
        and record.get("protocol_sha256") == base["identity"]["payload_sha256"]
        and record.get("builder_sha256") == base["identity"]["builder_sha256"]
        and record.get("candidate_name") == base["candidate"]["name"]
        and record.get("selected_alpha") == selected_alpha
        and record.get("runtime") == runtime["runtime_probe"]
        and receipt_source.get("base_gears_protocol_payload_sha256") == source["base_gears_protocol_payload_sha256"]
        and receipt_source.get("prepare_candidate_record") == source["exact_prepare_v4"]["candidate_record"]
        and receipt_source.get("native_train_only_h5ad") == source["exact_prepare_v4"]["native_train_only_h5ad"]
        and selection.get("train_condition_count") == base["training"]["selection_split"]["train_condition_count"]
        and selection.get("train_condition_labels_sha256")
        == base["training"]["selection_split"]["train_condition_labels_sha256"]
        and selection.get("validation_condition_count")
        == base["training"]["selection_split"]["validation_condition_count"]
        and selection.get("validation_condition_labels_sha256")
        == base["training"]["selection_split"]["validation_condition_labels_sha256"]
        and selection.get("metric") == base["training"]["selection_metric"]
        and selection.get("selected_alpha") == selected_alpha
        and selection.get("selected_strictly_improves_both_scopes_over_alpha_1") is True
        and final_refit
        == {
            "condition_count": base["training"]["final_refit"]["canonical_outer_train_condition_count"],
            "condition_labels_sha256": base["training"]["final_refit"]["canonical_outer_train_condition_labels_sha256"],
            "alpha": selected_alpha,
            "uses_all_canonical_outer_train_conditions": True,
        }
        and record.get("decision_path_exposure") == base["decision_path_exposure"]
        and record.get("prospective_test_blinding") is False
        and record.get("benchmark_status") == "NOT_RUN"
        and record.get("benchmark_passed") is None
        and record.get("scientifically_validated") is False
        and record.get("promotion_eligible") is False
        and record.get("production_promoted") is False
        and record.get("registry_or_default_route_changed") is False
    ):
        raise ValidationError("candidate receipt contract changed")

    arrays = baseline.get("arrays")
    feature_ids = baseline.get("feature_ids")
    target_ids = baseline.get("target_ids")
    target_symbols = baseline.get("target_symbols")
    pairs = (
        [
            {"target_id": target_id, "symbol": symbol}
            for target_id, symbol in zip(target_ids, target_symbols, strict=True)
        ]
        if isinstance(target_ids, list) and isinstance(target_symbols, list) and len(target_ids) == len(target_symbols)
        else None
    )
    inference = protocol["inference"]
    target_axis = base["candidate"]["target_axis"]
    if not (
        baseline.get("schema_version") == "praxis.golden-additive-train-only-baseline.v1"
        and baseline.get("candidate_name") == base["candidate"]["name"]
        and baseline.get("algorithm") == base["candidate"]["algorithm"]
        and baseline.get("prediction") == base["candidate"]["prediction"]
        and baseline.get("selected_alpha") == selected_alpha
        and isinstance(feature_ids, list)
        and len(feature_ids) == inference["ordered_feature_count"]
        and len(feature_ids) == len(set(feature_ids))
        and builder._fingerprint(feature_ids) == baseline.get("feature_ids_sha256")
        and baseline.get("feature_ids_sha256") == inference["ordered_feature_ids_sha256"]
        and baseline.get("feature_ids_sha256") == base["candidate"]["feature_axis"]["sha256"]
        and isinstance(target_ids, list)
        and isinstance(target_symbols, list)
        and len(target_ids) == inference["target_axis_count"] == target_axis["count"]
        and len(target_ids) == len(set(target_ids))
        and len(target_symbols) == len(set(target_symbols))
        and set(target_ids).issubset(feature_ids)
        and builder._fingerprint(target_ids) == baseline.get("target_ids_sha256")
        and builder._fingerprint(target_symbols) == baseline.get("target_symbols_sha256")
        and builder._fingerprint(pairs) == baseline.get("target_id_symbol_pairs_sha256")
        and baseline.get("target_ids_sha256") == inference["target_ids_sha256"] == target_axis["target_ids_sha256"]
        and baseline.get("target_symbols_sha256")
        == inference["target_symbols_sha256"]
        == target_axis["target_symbols_sha256"]
        and baseline.get("target_id_symbol_pairs_sha256")
        == inference["target_id_symbol_pairs_sha256"]
        == target_axis["target_id_symbol_pairs_sha256"]
        and baseline.get("outer_train_condition_labels_sha256")
        == base["training"]["final_refit"]["canonical_outer_train_condition_labels_sha256"]
        and isinstance(arrays, dict)
        and set(arrays) == {"linear_coefficients.npy", "linear_intercept.npy"}
    ):
        raise ValidationError("candidate baseline contract changed")

    scopes = (
        baseline.get("outer_train_seen_target_ids"),
        baseline.get("outer_train_unseen_target_ids"),
        selection.get("selection_fit_seen_target_ids"),
        selection.get("selection_fit_unseen_target_ids"),
    )
    if not all(isinstance(value, list) for value in scopes):
        raise ValidationError("candidate fitted target scope is invalid")
    outer_seen, outer_unseen, selection_seen, selection_unseen = scopes
    if not (
        set(outer_seen).isdisjoint(outer_unseen)
        and set(outer_seen).union(outer_unseen) == set(target_ids)
        and set(selection_seen).isdisjoint(selection_unseen)
        and set(selection_seen).union(selection_unseen) == set(target_ids)
    ):
        raise ValidationError("candidate fitted target scope changed")

    rows = selection.get("alpha_grid_results")
    selected_rows = (
        [item for item in rows if item.get("alpha") == selected_alpha]
        if isinstance(rows, list) and all(isinstance(item, dict) for item in rows)
        else []
    )
    expected_metrics = base["training"]["expected_selected_internal_metrics"]
    if not (
        isinstance(rows, list)
        and [item.get("alpha") for item in rows] == list(map(float, base["training"]["alpha_grid"]))
        and len(selected_rows) == 1
        and all(
            math.isclose(
                selected_rows[0].get(name, math.nan),
                expected_metrics[name],
                rel_tol=0.0,
                abs_tol=expected_metrics["absolute_tolerance"],
            )
            for name in (
                "single_condition_macro_mse",
                "combination_condition_macro_mse",
                "normalized_max_score",
            )
        )
    ):
        raise ValidationError("candidate internal selection receipt changed")

    for name in sorted(arrays):
        if {key: arrays[name].get(key) for key in ("shape", "dtype")} != {
            key: inference["arrays"][name][key] for key in ("shape", "dtype")
        }:
            raise ValidationError("candidate array metadata changed")
        if record.get("artifacts", {}).get(name) != arrays[name]:
            raise ValidationError("candidate receipt and baseline array records differ")
    if record.get("artifacts", {}).get("baseline.json") != files["baseline.json"]:
        raise ValidationError("candidate receipt does not bind baseline metadata")
    coefficients = _array(root, "linear_coefficients.npy", arrays["linear_coefficients.npy"], builder)
    intercept = _array(root, "linear_intercept.npy", arrays["linear_intercept.npy"], builder)
    if coefficients.shape != (len(target_ids), len(feature_ids)) or intercept.shape != (len(feature_ids),):
        raise ValidationError("candidate coefficient geometry changed")
    return baseline, coefficients, intercept


def _macro_mse(losses: list[float]) -> float:
    if not losses or not all(map(math.isfinite, losses)):
        raise ValidationError("validation loss is non-finite or empty")
    return math.fsum(losses) / len(losses)


def _score(
    *,
    truth: np.ndarray,
    condition_records: list[dict[str, Any]],
    target_ids: list[str],
    target_symbols: list[str],
    coefficients: np.ndarray,
    intercept: np.ndarray,
    gates: dict[str, Any],
) -> dict[str, Any]:
    if (
        truth.ndim != 2
        or coefficients.shape != (len(target_ids), truth.shape[1])
        or intercept.shape != (truth.shape[1],)
        or len(target_ids) != len(target_symbols)
        or not np.isfinite(truth).all()
        or not np.isfinite(coefficients).all()
        or not np.isfinite(intercept).all()
    ):
        raise ValidationError("validation prediction geometry changed")
    target_position = {value: index for index, value in enumerate(target_ids)}
    symbol_to_id = dict(zip(target_symbols, target_ids, strict=True))
    id_to_symbol = dict(zip(target_ids, target_symbols, strict=True))
    predictions = []
    routing = []
    for record in condition_records:
        symbols = record.get("targets")
        feature_ids = record.get("target_feature_ids")
        if not (
            isinstance(symbols, list)
            and isinstance(feature_ids, list)
            and len(symbols) == len(feature_ids) in {1, 2}
            and len(symbols) == len(set(symbols))
            and len(feature_ids) == len(set(feature_ids))
        ):
            raise ValidationError("validation target mapping is invalid")
        for symbol, feature_id in zip(symbols, feature_ids, strict=True):
            if (symbol in symbol_to_id and symbol_to_id[symbol] != feature_id) or (
                feature_id in id_to_symbol and id_to_symbol[feature_id] != symbol
            ):
                raise ValidationError("validation target symbol-to-feature mapping changed")
        seen = [feature_id for feature_id in feature_ids if feature_id in target_position]
        value = intercept.copy()
        for feature_id in seen:
            value += coefficients[target_position[feature_id]]
        unseen = [feature_id for feature_id in feature_ids if feature_id not in target_position]
        predictions.append(value)
        routing.append(
            {
                "seen_target_feature_ids": seen,
                "unseen_target_feature_ids": unseen,
                "seen_targets": [
                    symbol
                    for symbol, feature_id in zip(symbols, feature_ids, strict=True)
                    if feature_id in target_position
                ],
                "unseen_targets": [
                    symbol
                    for symbol, feature_id in zip(symbols, feature_ids, strict=True)
                    if feature_id not in target_position
                ],
            }
        )
    predicted = np.stack(predictions).astype(np.float64, copy=False)
    squared = np.square(predicted - truth, dtype=np.float64)
    losses = np.sum(squared, axis=1, dtype=np.float64) / truth.shape[1]
    if not np.isfinite(losses).all():
        raise ValidationError("validation loss is non-finite")
    per_condition = []
    by_scope: dict[str, list[float]] = {"single": [], "combination": []}
    for record, route, loss in zip(condition_records, routing, losses, strict=True):
        scope = record.get("scope")
        if scope not in by_scope:
            raise ValidationError("validation scope changed")
        value = float(loss)
        by_scope[scope].append(value)
        per_condition.append(
            {
                "condition_id": record["condition_id"],
                "targets": record["targets"],
                "target_feature_ids": record["target_feature_ids"],
                "scope": scope,
                "route": "intercept_plus_seen_target_coefficients_unseen_targets_zero",
                **route,
                "mse": value,
            }
        )
    aggregate = {
        "single_condition_macro_mse": _macro_mse(by_scope["single"]),
        "combination_condition_macro_mse": _macro_mse(by_scope["combination"]),
        "all_condition_macro_mse": _macro_mse(list(map(float, losses))),
    }
    passed = bool(
        aggregate["single_condition_macro_mse"] < gates["single_condition_macro_mse_strictly_below"]
        and aggregate["combination_condition_macro_mse"] < gates["combination_condition_macro_mse_strictly_below"]
    )
    return {
        "metric": "condition_macro_full_feature_delta_mse",
        "feature_count": truth.shape[1],
        "reduction_dtype": "float64",
        "prediction": "intercept_plus_sum_of_seen_target_coefficients_with_unseen_target_coefficient_zero",
        "condition_count": len(condition_records),
        "single_condition_count": len(by_scope["single"]),
        "combination_condition_count": len(by_scope["combination"]),
        "conditions_with_unseen_targets": sum(bool(item["unseen_targets"]) for item in routing),
        "aggregate": aggregate,
        "per_condition": per_condition,
        "gate": {
            "single_condition_macro_mse_strictly_below": gates["single_condition_macro_mse_strictly_below"],
            "combination_condition_macro_mse_strictly_below": gates["combination_condition_macro_mse_strictly_below"],
            "development_validation_thresholds_passed": passed,
        },
    }


def _write_new_file(output: Path, payload: bytes, builder) -> None:
    output = output.absolute()
    parent, parent_fd = builder._validated_output_parent(output)
    temporary = f".{output.name}.{os.getpid()}.{os.urandom(8).hex()}"
    descriptor = -1
    try:
        try:
            os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValidationError("output must be write-new")
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_fd,
        )
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        builder._publish(Path(temporary), Path(output.name), parent_fd=parent_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)


def evaluate(*, protocol_path: Path, truth_bundle: Path, candidate_root: Path, output: Path) -> dict[str, Any]:
    protocol, base, builder = _load_protocol(protocol_path)
    _require_frozen(protocol)
    reuse = _verify_reuse_disclosure(protocol, builder)
    runtime = _verify_runtime(protocol, base, builder)
    if os.path.lexists(output):
        raise ValidationError("output must be write-new")
    metadata, truth = _verify_truth_bundle(truth_bundle.absolute(), protocol, builder)
    baseline, coefficients, intercept = _verify_candidate(candidate_root.absolute(), protocol, base, builder, runtime)
    if not (
        metadata["features"]["ordered_feature_ids_sha256"] == baseline["feature_ids_sha256"]
        and metadata["features"]["ordered_feature_symbols_sha256"]
        == protocol["inference"]["ordered_feature_symbols_sha256"]
    ):
        raise ValidationError("candidate and truth ordered feature identity differ")
    metrics = _score(
        truth=truth,
        condition_records=metadata["conditions"],
        target_ids=baseline["target_ids"],
        target_symbols=baseline["target_symbols"],
        coefficients=coefficients,
        intercept=intercept,
        gates=protocol["validation_gate"],
    )
    passed = metrics["gate"]["development_validation_thresholds_passed"]
    result = {
        "schema_version": "praxis.golden-additive-train-only-validation-result.v1",
        "record_role": "exposed_reused_development_validation_not_independent_not_test_not_scientific_promotion",
        "protocol_sha256": protocol["identity"]["payload_sha256"],
        "base_protocol_payload_sha256": base["identity"]["payload_sha256"],
        "evaluator_sha256": protocol["identity"]["evaluator_sha256"],
        "candidate_name": base["candidate"]["name"],
        "truth_bundle": protocol["truth_bundle"]["files"],
        "candidate_artifact": protocol["candidate_artifact"]["files"],
        "validation_evidence_class": "exposed_reused_development_validation",
        "independent": False,
        "access_round": reuse["access_round"],
        "prior_validation_result": reuse["prior_validation_result"],
        "candidate_iteration_occurred_after_prior_validation_failure": reuse[
            "candidate_iteration_occurred_after_prior_validation_failure"
        ],
        "candidate_model_class_selected_after_prior_golden_validation_failure": reuse[
            "candidate_model_class_selected_after_prior_golden_validation_failure"
        ],
        "decision_path_is_adaptive_to_prior_golden_validation_failure": reuse[
            "decision_path_is_adaptive_to_prior_golden_validation_failure"
        ],
        "candidate_hyperparameters_selected_from_golden_validation_values": reuse[
            "candidate_hyperparameters_selected_from_golden_validation_values"
        ],
        "prospective_test_blinding": False,
        "prospective_test_blinding_reason": reuse["prospective_test_blinding_reason"],
        "metrics": metrics,
        "execution": {
            "inputs": ["frozen_validation_truth_bundle", "frozen_candidate_artifact"],
            "full_golden_pack_received_by_evaluator": False,
            "prepared_train_h5ad_received_by_evaluator": False,
            "raw_golden_validation_expression_received_by_evaluator": False,
            "golden_test_expression_used": False,
            "golden_test_outcomes_used": False,
            "test_loader_present": False,
            "network_used": False,
            "reduction_runtime": runtime,
        },
        "states": {
            "development_validation_thresholds_passed": passed,
            "independent_validation_passed": False,
            "future_separately_authorized_descriptive_test_eligible": False,
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
            "registry_or_default_route_changed": False,
        },
    }
    _write_new_file(output, builder._canonical_bytes(result) + b"\n", builder)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=_VALIDATION_PROTOCOL)
    parser.add_argument("--truth-bundle", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    result = evaluate(
        protocol_path=arguments.protocol,
        truth_bundle=arguments.truth_bundle,
        candidate_root=arguments.candidate_root,
        output=arguments.output,
    )
    print(json.dumps(result["metrics"]["gate"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

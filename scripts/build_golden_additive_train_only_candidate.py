#!/usr/bin/env python3
"""Fit the frozen additive-ridge Candidate-2 from the exact train-only prepare."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import shutil
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).parents[1]
_PROTOCOL = _ROOT / "data/golden/norman_2019/additive_train_only_protocol.json"
_GEARS_PROTOCOL = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"
_GEARS_BUILDER_PATH = _ROOT / "scripts/build_golden_gears_train_only_candidate.py"
_GEARS_TRAIN_PATH = _ROOT / "scripts/train_golden_gears_train_only_candidate.py"


def _script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GEARS_BUILDER = _script("golden_gears_builder_for_additive", _GEARS_BUILDER_PATH)
_GEARS_TRAIN = _script("golden_gears_train_for_additive", _GEARS_TRAIN_PATH)
CandidateBuildError = _GEARS_BUILDER.CandidateBuildError
_reject_duplicate_keys = _GEARS_BUILDER._reject_duplicate_keys
_canonical_bytes = _GEARS_BUILDER._canonical_bytes
_fingerprint = _GEARS_BUILDER._fingerprint
_sha256 = _GEARS_BUILDER._sha256
_file_record = _GEARS_BUILDER._file_record
_validated_output_parent = _GEARS_BUILDER._validated_output_parent
_new_staging_directory = _GEARS_BUILDER._new_staging_directory
_assert_named_directory_inode = _GEARS_BUILDER._assert_named_directory_inode
_publish = _GEARS_BUILDER._publish


def _load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                CandidateBuildError("candidate protocol contains non-finite JSON")
            ),
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBuildError("candidate protocol is unavailable") from exc
    if value.get("schema_version") != "praxis.golden-additive-train-only-protocol.v1":
        raise CandidateBuildError("unsupported candidate protocol")
    expected = value.get("identity", {}).get("payload_sha256")
    copy = json.loads(_canonical_bytes(value))
    copy["identity"]["payload_sha256"] = None
    if expected != _fingerprint(copy):
        raise CandidateBuildError("candidate protocol payload hash changed")
    if value["identity"].get("builder_sha256") != _sha256(Path(__file__)):
        raise CandidateBuildError("candidate builder differs from the frozen protocol")
    return value


def _load_base_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    base = _GEARS_BUILDER._load_protocol(_GEARS_PROTOCOL)
    source = protocol["train_only_source"]
    if not (
        source["base_gears_protocol_payload_sha256"] == base["identity"]["payload_sha256"]
        and protocol["identity"]["base_gears_builder_sha256"] == _sha256(_GEARS_BUILDER_PATH)
        and protocol["identity"]["base_gears_train_runner_sha256"] == _sha256(_GEARS_TRAIN_PATH)
    ):
        raise CandidateBuildError("base train-only protocol identity changed")
    return base


def _condition_means(path: Path, labels: list[str], n_features: int) -> dict[str, np.ndarray]:
    import anndata

    source = anndata.read_h5ad(path, backed="r")
    try:
        names = sorted(set(labels))
        sums = {name: np.zeros(n_features, dtype=np.float64) for name in names}
        counts = {name: 0 for name in names}
        for start in range(0, source.n_obs, 512):
            stop = min(start + 512, source.n_obs)
            block_labels = np.asarray(labels[start:stop], dtype=object)
            block = source.X[start:stop]
            for name in sorted(set(block_labels.tolist())):
                rows = np.flatnonzero(block_labels == name)
                selected = block[rows].astype(np.float64)
                sums[name] += np.asarray(selected.sum(axis=0), dtype=np.float64).reshape(-1)
                counts[name] += len(rows)
        means = {name: sums[name] / counts[name] for name in names}
        if not all(counts.values()) or not all(np.isfinite(value).all() for value in means.values()):
            raise CandidateBuildError("condition means are empty or non-finite")
        return means
    finally:
        source.file.close()


def _design(conditions: list[str], target_symbols: list[str]) -> tuple[np.ndarray, list[str], list[str]]:
    positions = {symbol: index for index, symbol in enumerate(target_symbols)}
    value = np.zeros((len(conditions), len(target_symbols)), dtype=np.float64)
    for row, condition in enumerate(conditions):
        for symbol in _GEARS_BUILDER._canonical_targets(condition):
            value[row, positions[symbol]] = 1.0
    seen = [target_symbols[index] for index in np.flatnonzero(value.sum(axis=0) > 0)]
    unseen = [symbol for symbol in target_symbols if symbol not in set(seen)]
    return value, seen, unseen


def _fit(
    conditions: list[str],
    deltas: dict[str, np.ndarray],
    target_symbols: list[str],
    alpha: float,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    design, seen, unseen = _design(conditions, target_symbols)
    response = np.stack([deltas[condition] for condition in conditions]).astype(np.float64, copy=False)
    x_mean = design.mean(axis=0, dtype=np.float64)
    y_mean = response.mean(axis=0, dtype=np.float64)
    centered_x = design - x_mean
    centered_y = response - y_mean
    coefficients = np.linalg.solve(
        centered_x.T @ centered_x + alpha * np.eye(len(target_symbols), dtype=np.float64),
        centered_x.T @ centered_y,
    )
    intercept = y_mean - x_mean @ coefficients
    if unseen and not np.array_equal(
        coefficients[[target_symbols.index(value) for value in unseen]],
        np.zeros((len(unseen), response.shape[1]), dtype=np.float64),
    ):
        raise CandidateBuildError("internal-validation-only target acquired a nonzero coefficient")
    if not np.isfinite(coefficients).all() or not np.isfinite(intercept).all():
        raise CandidateBuildError("ridge fit is non-finite")
    return coefficients, intercept, seen, unseen


def _metrics(
    conditions: list[str],
    deltas: dict[str, np.ndarray],
    target_symbols: list[str],
    coefficients: np.ndarray,
    intercept: np.ndarray,
    thresholds: dict[str, float],
) -> dict[str, float]:
    positions = {symbol: index for index, symbol in enumerate(target_symbols)}
    losses: dict[int, list[float]] = {1: [], 2: []}
    for condition in conditions:
        targets = _GEARS_BUILDER._canonical_targets(condition)
        prediction = intercept + coefficients[[positions[value] for value in targets]].sum(axis=0)
        losses[len(targets)].append(float(np.mean(np.square(prediction - deltas[condition]), dtype=np.float64)))
    if not losses[1] or not losses[2]:
        raise CandidateBuildError("internal validation must contain singles and combinations")
    single = float(np.mean(losses[1], dtype=np.float64))
    combination = float(np.mean(losses[2], dtype=np.float64))
    return {
        "single_condition_macro_mse": single,
        "combination_condition_macro_mse": combination,
        "normalized_max_score": max(single / thresholds["single"], combination / thresholds["combination"]),
    }


def _choose_alpha(rows: list[dict[str, float]], comparator_alpha: float) -> dict[str, float]:
    selected = min(rows, key=lambda row: (row["normalized_max_score"], row["alpha"]))
    comparator = next((row for row in rows if row["alpha"] == comparator_alpha), None)
    if comparator is None or not (
        selected["single_condition_macro_mse"] < comparator["single_condition_macro_mse"]
        and selected["combination_condition_macro_mse"] < comparator["combination_condition_macro_mse"]
    ):
        raise CandidateBuildError("selected alpha does not improve both scopes over alpha=1")
    return selected


def _save_array(path: Path, value: np.ndarray) -> dict[str, Any]:
    if value.dtype != np.float64 or not np.isfinite(value).all():
        raise CandidateBuildError("model array must be finite float64")
    np.save(path, value, allow_pickle=False)
    loaded = np.load(path, allow_pickle=False)
    if loaded.dtype != np.float64 or loaded.shape != value.shape or not np.array_equal(loaded, value):
        raise CandidateBuildError("model array round-trip changed")
    return {
        "filename": path.name,
        **_file_record(path, single_link=True),
        "shape": list(value.shape),
        "dtype": "float64",
    }


def _prepare_data(
    prepare_root: Path, protocol: dict[str, Any], base: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    prepare_record, prepare_record_sha256 = _GEARS_TRAIN._verify_prepare_root(prepare_root, _GEARS_BUILDER, base)
    expected = protocol["train_only_source"]["exact_prepare_v4"]
    record_file = _file_record(prepare_root / "candidate-record.json", single_link=True)
    h5ad = prepare_root / "input/native_train_only.h5ad"
    h5ad_file = _file_record(h5ad, single_link=True)
    if (
        prepare_record_sha256 != expected["candidate_record"]["sha256"]
        or record_file != expected["candidate_record"]
        or h5ad_file != expected["native_train_only_h5ad"]
    ):
        raise CandidateBuildError("exact prepare v4 identity changed")
    split = _GEARS_TRAIN._verify_h5ad(h5ad, base, _GEARS_BUILDER)

    import anndata

    source = anndata.read_h5ad(h5ad, backed="r")
    try:
        labels = list(map(str, source.obs["condition"]))
        feature_ids = list(map(str, source.var_names))
        feature_symbols = list(map(str, source.var[base["pack"]["feature_symbol_field"]]))
    finally:
        source.file.close()
    if (
        _fingerprint(feature_ids) != base["pack"]["feature_ids_sha256"]
        or _fingerprint(feature_symbols) != base["pack"]["feature_symbols_sha256"]
        or len(feature_symbols) != len(set(feature_symbols))
    ):
        raise CandidateBuildError("feature or symbol mapping identity changed")
    means = _condition_means(h5ad, labels, len(feature_ids))
    control = means.pop("ctrl")
    deltas = {condition: value - control for condition, value in means.items()}
    symbol_to_id = dict(zip(feature_symbols, feature_ids, strict=True))
    all_symbols = {target for condition in deltas for target in _GEARS_BUILDER._canonical_targets(condition)}
    if not all_symbols.issubset(symbol_to_id):
        raise CandidateBuildError("condition target is absent from the feature mapping")
    target_symbols = sorted(all_symbols, key=symbol_to_id.__getitem__)
    target_ids = [symbol_to_id[value] for value in target_symbols]
    pairs = [
        {"target_id": target_id, "symbol": symbol} for target_id, symbol in zip(target_ids, target_symbols, strict=True)
    ]
    expected_axis = protocol["candidate"]["target_axis"]
    if not (
        len(target_ids) == expected_axis["count"]
        and _fingerprint(target_ids) == expected_axis["target_ids_sha256"]
        and _fingerprint(target_symbols) == expected_axis["target_symbols_sha256"]
        and _fingerprint(pairs) == expected_axis["target_id_symbol_pairs_sha256"]
    ):
        raise CandidateBuildError("target axis identity changed")
    return {
        "prepare_record": prepare_record,
        "prepare_record_file": record_file,
        "h5ad_file": h5ad_file,
        "split": split,
    }, {
        "feature_ids": feature_ids,
        "target_ids": target_ids,
        "target_symbols": target_symbols,
        "deltas": deltas,
    }


def build(*, prepare_root: Path, output: Path, protocol_path: Path = _PROTOCOL) -> dict[str, Any]:
    protocol = _load_protocol(protocol_path.absolute())
    base = _load_base_protocol(protocol)
    runtime = _GEARS_TRAIN._verify_runtime(_GEARS_BUILDER, base)
    prepare_root = prepare_root.absolute()
    source, data = _prepare_data(prepare_root, protocol, base)
    split = source["split"]
    train_conditions = sorted(set(split["train"]) - {"ctrl"})
    validation_conditions = list(split["val"])
    frozen_split = protocol["training"]["selection_split"]
    if not (
        len(train_conditions) == frozen_split["train_condition_count"]
        and _fingerprint(train_conditions) == frozen_split["train_condition_labels_sha256"]
        and len(validation_conditions) == frozen_split["validation_condition_count"]
        and _fingerprint(validation_conditions) == frozen_split["validation_condition_labels_sha256"]
        and sum(len(_GEARS_BUILDER._canonical_targets(value)) == 1 for value in validation_conditions)
        == frozen_split["validation_single_condition_count"]
        and sum(len(_GEARS_BUILDER._canonical_targets(value)) == 2 for value in validation_conditions)
        == frozen_split["validation_combination_condition_count"]
    ):
        raise CandidateBuildError("frozen 93/11 selection split changed")
    target_symbols = data["target_symbols"]
    selection_fit_seen: list[str] | None = None
    selection_fit_unseen: list[str] | None = None
    rows = []
    for alpha in protocol["training"]["alpha_grid"]:
        coefficients, intercept, seen, unseen = _fit(train_conditions, data["deltas"], target_symbols, float(alpha))
        if selection_fit_seen is None:
            selection_fit_seen, selection_fit_unseen = seen, unseen
        elif (seen, unseen) != (selection_fit_seen, selection_fit_unseen):
            raise CandidateBuildError("alpha grid changed the fitted target scope")
        rows.append(
            {
                "alpha": float(alpha),
                **_metrics(
                    validation_conditions,
                    data["deltas"],
                    target_symbols,
                    coefficients,
                    intercept,
                    protocol["training"]["selection_thresholds"],
                ),
            }
        )
    selected = _choose_alpha(rows, float(protocol["training"]["comparator_alpha"]))
    if selected["alpha"] != protocol["training"]["expected_selected_alpha"]:
        raise CandidateBuildError("selected alpha changed from the frozen expectation")
    expected_metrics = protocol["training"]["expected_selected_internal_metrics"]
    if any(
        not math.isclose(
            selected[name], expected_metrics[name], rel_tol=0.0, abs_tol=expected_metrics["absolute_tolerance"]
        )
        for name in (
            "single_condition_macro_mse",
            "combination_condition_macro_mse",
            "normalized_max_score",
        )
    ):
        raise CandidateBuildError("selected alpha internal metric receipt changed")
    outer_conditions = sorted(data["deltas"])
    expected_refit = protocol["training"]["final_refit"]
    if not (
        len(outer_conditions) == expected_refit["canonical_outer_train_condition_count"]
        and _fingerprint(outer_conditions) == expected_refit["canonical_outer_train_condition_labels_sha256"]
        and selected["alpha"] == expected_refit["alpha"]
    ):
        raise CandidateBuildError("outer-train final refit scope changed")
    coefficients, intercept, outer_seen, outer_unseen = _fit(
        outer_conditions, data["deltas"], target_symbols, selected["alpha"]
    )

    output = output.absolute()
    parent, parent_fd = _validated_output_parent(output)
    staging_name = ""
    staging_fd = -1
    original_cwd_fd = -1
    try:
        try:
            os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise CandidateBuildError("output must be write-new")
        staging_name, staging_fd = _new_staging_directory(parent_fd, output.name)
        original_cwd_fd = os.open(".", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        os.fchdir(staging_fd)
        staging = Path(".")
        arrays = {
            "linear_coefficients.npy": _save_array(staging / "linear_coefficients.npy", coefficients),
            "linear_intercept.npy": _save_array(staging / "linear_intercept.npy", intercept),
        }
        mapping = [
            {"target_id": feature_id, "symbol": symbol}
            for feature_id, symbol in zip(data["target_ids"], target_symbols, strict=True)
        ]
        baseline = {
            "schema_version": "praxis.golden-additive-train-only-baseline.v1",
            "candidate_name": protocol["candidate"]["name"],
            "algorithm": protocol["candidate"]["algorithm"],
            "selected_alpha": selected["alpha"],
            "prediction": "linear_intercept_plus_sum_of_target_rows_from_linear_coefficients",
            "feature_ids": data["feature_ids"],
            "feature_ids_sha256": _fingerprint(data["feature_ids"]),
            "target_ids": data["target_ids"],
            "target_ids_sha256": _fingerprint(data["target_ids"]),
            "target_symbols": target_symbols,
            "target_symbols_sha256": _fingerprint(target_symbols),
            "target_id_symbol_pairs_sha256": _fingerprint(mapping),
            "outer_train_condition_labels_sha256": _fingerprint(outer_conditions),
            "outer_train_seen_target_ids": [data["target_ids"][target_symbols.index(value)] for value in outer_seen],
            "outer_train_unseen_target_ids": [
                data["target_ids"][target_symbols.index(value)] for value in outer_unseen
            ],
            "arrays": arrays,
        }
        (staging / "baseline.json").write_bytes(_canonical_bytes(baseline) + b"\n")
        artifacts = {
            "baseline.json": _file_record(staging / "baseline.json", single_link=True),
            **arrays,
        }
        exposure = protocol["decision_path_exposure"]
        record = {
            "schema_version": protocol["claim_ceiling"]["output_schema_version"],
            "record_role": protocol["claim_ceiling"]["output_record_role"],
            "candidate_name": protocol["candidate"]["name"],
            "selected_alpha": selected["alpha"],
            "protocol_sha256": protocol["identity"]["payload_sha256"],
            "builder_sha256": protocol["identity"]["builder_sha256"],
            "runtime": runtime,
            "train_only_source": {
                "base_gears_protocol_payload_sha256": base["identity"]["payload_sha256"],
                "prepare_candidate_record": source["prepare_record_file"],
                "native_train_only_h5ad": source["h5ad_file"],
            },
            "internal_selection": {
                "train_condition_count": len(train_conditions),
                "train_condition_labels_sha256": _fingerprint(train_conditions),
                "validation_condition_count": len(validation_conditions),
                "validation_condition_labels_sha256": _fingerprint(validation_conditions),
                "selection_fit_seen_target_ids": [
                    data["target_ids"][target_symbols.index(value)] for value in selection_fit_seen or []
                ],
                "selection_fit_unseen_target_ids": [
                    data["target_ids"][target_symbols.index(value)] for value in selection_fit_unseen or []
                ],
                "metric": protocol["training"]["selection_metric"],
                "alpha_grid_results": rows,
                "selected_alpha": selected["alpha"],
                "selected_strictly_improves_both_scopes_over_alpha_1": True,
            },
            "final_refit": {
                "condition_count": len(outer_conditions),
                "condition_labels_sha256": _fingerprint(outer_conditions),
                "alpha": selected["alpha"],
                "uses_all_canonical_outer_train_conditions": True,
            },
            "artifacts": artifacts,
            "decision_path_exposure": exposure,
            "prospective_test_blinding": False,
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
            "registry_or_default_route_changed": False,
        }
        (staging / "candidate-record.json").write_bytes(_canonical_bytes(record) + b"\n")
        _assert_named_directory_inode(parent_fd, staging_name, staging_fd)
        _publish(Path(staging_name), Path(output.name), parent_fd=parent_fd)
        _assert_named_directory_inode(parent_fd, output.name, staging_fd)
        os.fchdir(original_cwd_fd)
        return record
    except BaseException:
        if parent_fd >= 0:
            os.fchdir(parent_fd)
        if staging_name:
            shutil.rmtree(staging_name, ignore_errors=True)
        if original_cwd_fd >= 0:
            os.fchdir(original_cwd_fd)
        raise
    finally:
        if staging_fd >= 0:
            os.close(staging_fd)
        if original_cwd_fd >= 0:
            os.close(original_cwd_fd)
        os.close(parent_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=_PROTOCOL)
    parser.add_argument("--prepare-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    build(prepare_root=arguments.prepare_root, output=arguments.output, protocol_path=arguments.protocol)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

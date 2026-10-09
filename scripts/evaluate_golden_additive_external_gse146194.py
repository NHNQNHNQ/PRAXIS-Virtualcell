#!/usr/bin/env python3
"""Run one frozen GSE146194 external stress test, never P16 validation."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).parents[1]
_DEFAULT_PROTOCOL = _ROOT / "data/golden/norman_2019/external_gse146194_additive_protocol.json"
_ADDITIVE_PROTOCOL = _ROOT / "data/golden/norman_2019/additive_train_only_protocol.json"
_RUNTIME_VERIFIER = _ROOT / "scripts/evaluate_golden_additive_train_only_validation.py"
_INPUT_FILES = {
    "GSM4367986_exp8.matrix.mtx.gz",
    "GSM4367986_exp8.barcodes.tsv.gz",
    "GSM4367986_exp8.features.tsv.gz",
    "GSM4367986_exp8.cell_identities.csv.gz",
}
_CANDIDATE_FILES = {
    "baseline.json",
    "candidate-record.json",
    "linear_coefficients.npy",
    "linear_intercept.npy",
}
_COMPARATOR_FILES = {
    "baseline.json",
    "linear_coefficients.npy",
    "linear_intercept.npy",
}
_INTEGER_COORDINATE_LINES = re.compile(rb"(?:[1-9][0-9]*[ \t]+[1-9][0-9]*[ \t]+[1-9][0-9]*\r?\n)+")


class StressError(ValueError):
    """Fail-closed external-stress error."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StressError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _strict_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_bytes(),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(StressError(f"non-finite JSON value: {token}")),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StressError(f"invalid JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise StressError(f"expected a JSON object: {path.name}")
    return value


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise StressError(f"required verifier is unavailable: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _file_record(path: Path) -> dict[str, Any]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or path.is_symlink():
        raise StressError(f"unsafe file identity: {path.name}")
    return {"size_bytes": info.st_size, "sha256": _sha256(path)}


def _exact_inventory(root: Path, expected: set[str]) -> None:
    if root.is_symlink() or not root.is_dir():
        raise StressError("input root must be a regular directory")
    observed: set[str] = set()
    for path in root.rglob("*"):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise StressError("input inventory contains an unsafe entry")
        if stat.S_ISREG(info.st_mode):
            if info.st_nlink != 1:
                raise StressError("input inventory contains a linked file")
            observed.add(path.relative_to(root).as_posix())
    if observed != expected:
        raise StressError("input inventory changed")


def _checked_files(root: Path, records: dict[str, Any], expected: set[str]) -> dict[str, dict[str, Any]]:
    _exact_inventory(root, expected)
    if not isinstance(records, dict) or set(records) != expected:
        raise StressError("frozen file inventory is invalid")
    observed = {name: _file_record(root / name) for name in sorted(expected)}
    if observed != records:
        raise StressError("frozen file identity changed")
    return observed


def _load_protocol(path: Path) -> dict[str, Any]:
    protocol = _strict_json(path)
    if protocol.get("schema_version") != "praxis.golden-additive-gse146194-external-stress-protocol.v1":
        raise StressError("unsupported external stress protocol")
    identity = protocol.get("identity", {})
    copy = json.loads(_canonical_bytes(protocol))
    copy["identity"]["payload_sha256"] = None
    if not (
        identity.get("payload_hash_algorithm")
        == "sha256(canonical_json(protocol_with_identity.payload_sha256_set_to_null))"
        and identity.get("payload_sha256") == _fingerprint(copy)
        and identity.get("evaluator_path") == "scripts/evaluate_golden_additive_external_gse146194.py"
        and identity.get("evaluator_sha256") == _sha256(Path(__file__))
    ):
        raise StressError("external stress protocol identity changed")
    if protocol.get("implementation_status") != "FROZEN_EXECUTABLE":
        raise StressError("external stress protocol is not executable")
    if any(record.get("sha256") is None for record in protocol.get("external_dataset", {}).get("files", {}).values()):
        raise StressError("external asset identities are not frozen")
    prior = protocol.get("decision_path_exposure", {})
    comparator = protocol.get("comparator", {})
    if not (
        _file_record(_ROOT / prior["prior_golden_development_validation_result_path"])
        == {
            "size_bytes": prior["prior_golden_development_validation_result_size_bytes"],
            "sha256": prior["prior_golden_development_validation_result_sha256"],
        }
        and _file_record(_ROOT / comparator["model_card_relative_path"])
        == {
            "size_bytes": comparator["model_card_size_bytes"],
            "sha256": comparator["model_card_sha256"],
        }
    ):
        raise StressError("frozen source evidence identity changed")
    return protocol


def _verify_runtime(protocol: dict[str, Any]) -> dict[str, Any]:
    expected = protocol["runtime"]
    if not (
        expected.get("source_runtime_verifier_path") == "scripts/evaluate_golden_additive_train_only_validation.py"
        and expected.get("source_runtime_verifier_sha256") == _sha256(_RUNTIME_VERIFIER)
    ):
        raise StressError("frozen runtime verifier identity changed")
    verifier = _load_module("additive_external_runtime_verifier", _RUNTIME_VERIFIER)
    builder = verifier._builder()
    try:
        base = builder._load_protocol(_ADDITIVE_PROTOCOL)
        if base["identity"]["payload_sha256"] != protocol["candidate"]["base_protocol_payload_sha256"]:
            raise StressError("candidate source protocol identity changed")
        return verifier._verify_runtime(protocol, base, builder)
    except Exception as exc:
        raise StressError("frozen runtime identity changed") from exc


def _load_array(path: Path, shape: tuple[int, ...]) -> np.ndarray:
    try:
        value = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise StressError(f"invalid model array: {path.name}") from exc
    if value.shape != shape or value.dtype.str != "<f8" or not np.isfinite(value).all():
        raise StressError(f"model array contract changed: {path.name}")
    return np.asarray(value, dtype=np.float64)


def _load_model(
    root: Path,
    frozen: dict[str, Any],
    *,
    candidate: bool,
) -> tuple[list[str], list[str], np.ndarray, np.ndarray, list[str]]:
    expected = _CANDIDATE_FILES if candidate else _COMPARATOR_FILES
    _checked_files(root, frozen["files"], expected)
    metadata = _strict_json(root / "baseline.json")
    feature_ids = metadata.get("feature_ids")
    target_ids = metadata.get("target_ids")
    if not (
        isinstance(feature_ids, list)
        and len(feature_ids) == frozen["feature_count"]
        and len(set(feature_ids)) == len(feature_ids)
        and _fingerprint(feature_ids) == frozen["feature_ids_sha256"]
        and metadata.get("feature_ids_sha256") == frozen["feature_ids_sha256"]
        and isinstance(target_ids, list)
        and len(target_ids) == frozen["target_count"]
        and len(set(target_ids)) == len(target_ids)
        and _fingerprint(target_ids) == frozen["target_ids_sha256"]
        and metadata.get("target_ids_sha256") == frozen["target_ids_sha256"]
    ):
        raise StressError("model feature or target identity changed")
    if candidate:
        record = _strict_json(root / "candidate-record.json")
        if not (
            metadata.get("schema_version") == "praxis.golden-additive-train-only-baseline.v1"
            and metadata.get("candidate_name") == frozen["name"]
            and metadata.get("selected_alpha") == frozen["selected_alpha"]
            and record.get("candidate_name") == frozen["name"]
            and record.get("selected_alpha") == frozen["selected_alpha"]
            and record.get("protocol_sha256") == frozen["base_protocol_payload_sha256"]
            and record.get("scientifically_validated") is False
            and record.get("promotion_eligible") is False
            and record.get("production_promoted") is False
        ):
            raise StressError("candidate receipt semantics changed")
        seen_target_ids = metadata.get("outer_train_seen_target_ids")
        unseen_target_ids = metadata.get("outer_train_unseen_target_ids")
        if seen_target_ids != target_ids or unseen_target_ids != []:
            raise StressError("candidate seen-target identity changed")
    elif not (
        metadata.get("schema_version") == "vc.golden-baseline.v1"
        and metadata.get("model_name") == frozen["name"]
        and metadata.get("baseline") == "additive_linear"
        and metadata.get("algorithm") == "condition-level additive ridge"
    ):
        raise StressError("comparator receipt semantics changed")
    else:
        seen_target_ids = metadata.get("seen_train_target_ids")
        unseen_target_ids = metadata.get("unseen_train_target_ids")
        if not (
            isinstance(seen_target_ids, list)
            and isinstance(unseen_target_ids, list)
            and len(set(seen_target_ids)) == len(seen_target_ids)
            and len(set(unseen_target_ids)) == len(unseen_target_ids)
            and set(seen_target_ids).isdisjoint(unseen_target_ids)
            and set(seen_target_ids) | set(unseen_target_ids) == set(target_ids)
        ):
            raise StressError("comparator seen-target identity changed")
    coefficients = _load_array(root / "linear_coefficients.npy", (len(target_ids), len(feature_ids)))
    intercept = _load_array(root / "linear_intercept.npy", (len(feature_ids),))
    return feature_ids, target_ids, coefficients, intercept, seen_target_ids


def _predictions(
    targets: list[dict[str, Any]],
    target_ids: list[str],
    coefficients: np.ndarray,
    intercept: np.ndarray,
) -> dict[str, np.ndarray]:
    positions = {value: index for index, value in enumerate(target_ids)}
    requested = [record["ensembl_id"] for record in targets]
    if any(value not in positions for value in requested):
        raise StressError("external target is absent from a frozen model")
    return {record["symbol"]: intercept + coefficients[positions[record["ensembl_id"]]] for record in targets}


def _barcodes(path: Path, expected_count: int) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        rows = [line.rstrip("\r\n") for line in stream]
    if len(rows) != expected_count or any(not value or "\t" in value for value in rows) or len(set(rows)) != len(rows):
        raise StressError("external barcode contract changed")
    return rows


def _features(
    path: Path,
    expected_count: int,
    expected_type_counts: dict[str, int],
) -> tuple[list[str], list[str], np.ndarray]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        rows = [line.rstrip("\r\n").split("\t") for line in stream]
    if len(rows) != expected_count or any(len(row) != 3 or not row[0] or not row[1] for row in rows):
        raise StressError("external feature contract changed")
    identifiers = [row[0] for row in rows]
    symbols = [row[1] for row in rows]
    feature_types = [row[2] for row in rows]
    observed_type_counts = {value: feature_types.count(value) for value in set(feature_types)}
    if len(set(identifiers)) != len(identifiers) or observed_type_counts != expected_type_counts:
        raise StressError("external feature identity or type counts changed")
    return (
        identifiers,
        symbols,
        np.asarray([value == "Gene Expression" for value in feature_types], dtype=np.bool_),
    )


def _selected_groups(
    path: Path,
    selection: dict[str, Any],
    expected_rows: int,
    eligible_target_ids: set[str],
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    required = selection["required_cell_identity_columns"]
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != required:
            raise StressError("external cell-identity header changed")
        rows = list(reader)
    barcodes = [row["cell_barcode"] for row in rows]
    if len(rows) != expected_rows or len(set(barcodes)) != len(barcodes) or any(not value for value in barcodes):
        raise StressError("external cell-identity rows changed")

    targets = selection["targets"]
    target_filters = selection["target_common_filters"]
    by_guide = {record["sgID_A"]: record for record in targets}
    groups = {record["symbol"]: [] for record in targets}
    controls = {record["sgID_A"]: [] for record in selection["controls"]}
    control_filters = selection["control_common_filters"]
    eligible_metadata_targets: set[tuple[str, str, str]] = set()
    for row in rows:
        common = (
            row["good_coverage"] == str(target_filters["good_coverage"])
            and row["num_guides"] == str(target_filters["num_guides"])
            and row["number_of_cells"] == str(target_filters["number_of_cells"])
        )
        target_filter_match = common and all(
            row[key] == str(value)
            for key, value in target_filters.items()
            if key not in {"good_coverage", "num_guides", "number_of_cells"}
        )
        if target_filter_match and row["target"] in eligible_target_ids:
            eligible_metadata_targets.add((row["gene"], row["target"], row["sgID_A"]))
        target = by_guide.get(row["sgID_A"])
        if target is not None and target_filter_match:
            if row["gene"] != target["symbol"] or row["target"] != target["ensembl_id"]:
                raise StressError("external target metadata changed")
            groups[target["symbol"]].append(row["cell_barcode"])

        control_common = (
            row["good_coverage"] == str(control_filters["good_coverage"])
            and row["num_guides"] == str(control_filters["num_guides"])
            and row["number_of_cells"] == str(control_filters["number_of_cells"])
        )
        if (
            row["sgID_A"] in controls
            and control_common
            and all(
                row[key] == str(value)
                for key, value in control_filters.items()
                if key not in {"good_coverage", "num_guides", "number_of_cells"}
            )
        ):
            controls[row["sgID_A"]].append(row["cell_barcode"])

    for record in targets:
        if len(groups[record["symbol"]]) != record["expected_cells"]:
            raise StressError("external target cell count changed")
    for record in selection["controls"]:
        if len(controls[record["sgID_A"]]) != record["expected_cells"]:
            raise StressError("external control cell count changed")
    expected_metadata_targets = {(record["symbol"], record["ensembl_id"], record["sgID_A"]) for record in targets}
    if eligible_metadata_targets != expected_metadata_targets:
        raise StressError("external eligible target set changed")
    control_cells = [barcode for record in selection["controls"] for barcode in controls[record["sgID_A"]]]
    selected = [barcode for values in groups.values() for barcode in values]
    if (
        len(selected) != selection["expected_target_cells"]
        or len(control_cells) != selection["expected_control_cells"]
        or len(set(selected + control_cells)) != len(selected) + len(control_cells)
    ):
        raise StressError("external selected-cell identity changed")
    groups["__control__"] = control_cells
    return groups, {
        "metadata_rows": len(rows),
        "unique_metadata_barcodes": len(set(barcodes)),
        "target_cells": len(selected),
        "control_cells": len(control_cells),
        "eligible_metadata_target_count": len(eligible_metadata_targets),
        "target_cell_counts": {record["symbol"]: len(groups[record["symbol"]]) for record in targets},
        "control_cell_counts": {record["sgID_A"]: len(controls[record["sgID_A"]]) for record in selection["controls"]},
    }


def _parse_integer_block(block: bytes) -> np.ndarray:
    if not block or _INTEGER_COORDINATE_LINES.fullmatch(block) is None:
        raise StressError("external Matrix Market coordinate row is malformed")
    try:
        values = np.fromstring(block, dtype=np.int64, sep=" ")
    except ValueError as exc:
        raise StressError("external Matrix Market coordinate row is malformed") from exc
    if values.size != 3 * block.count(b"\n"):
        raise StressError("external Matrix Market coordinate row is malformed")
    return values.reshape((-1, 3))


def _selected_counts(
    path: Path,
    *,
    expected_shape: list[int],
    expected_entries: int,
    feature_rows: list[int],
    library_feature_rows: list[int],
    selected_columns: list[int],
) -> tuple[np.ndarray, np.ndarray, int]:
    row_count, column_count = expected_shape
    row_map = np.full(row_count, -1, dtype=np.int32)
    row_map[np.asarray(feature_rows, dtype=np.int64)] = np.arange(len(feature_rows), dtype=np.int32)
    library_row_mask = np.zeros(row_count, dtype=np.bool_)
    library_row_mask[np.asarray(library_feature_rows, dtype=np.int64)] = True
    if not np.all(library_row_mask[np.asarray(feature_rows, dtype=np.int64)]):
        raise StressError("candidate projection contains a non-expression feature")
    column_map = np.full(column_count, -1, dtype=np.int32)
    column_map[np.asarray(selected_columns, dtype=np.int64)] = np.arange(len(selected_columns), dtype=np.int32)
    counts = np.zeros((len(feature_rows), len(selected_columns)), dtype=np.float64)
    library_sizes = np.zeros(len(selected_columns), dtype=np.float64)
    parsed = 0
    with gzip.open(path, "rb") as stream:
        if stream.readline().rstrip(b"\r\n") != b"%%MatrixMarket matrix coordinate integer general":
            raise StressError("external Matrix Market header changed")
        line = stream.readline()
        while line.startswith(b"%"):
            line = stream.readline()
        try:
            dimensions = [int(value) for value in line.split()]
        except ValueError as exc:
            raise StressError("external Matrix Market dimensions are invalid") from exc
        if len(dimensions) != 3 or dimensions[:2] != expected_shape or dimensions[2] != expected_entries:
            raise StressError("external Matrix Market shape changed")
        tail = b""
        while True:
            chunk = stream.read(16 * 1024 * 1024)
            if not chunk:
                break
            data = tail + chunk
            boundary = data.rfind(b"\n")
            if boundary < 0:
                tail = data
                continue
            block = data[: boundary + 1]
            tail = data[boundary + 1 :]
            triples = _parse_integer_block(block)
            parsed += len(triples)
            rows = triples[:, 0] - 1
            columns = triples[:, 1] - 1
            values = triples[:, 2]
            if (
                np.any(rows < 0)
                or np.any(rows >= row_count)
                or np.any(columns < 0)
                or np.any(columns >= column_count)
                or np.any(values <= 0)
            ):
                raise StressError("external Matrix Market coordinate is out of range")
            selected_cells = column_map[columns]
            cell_mask = selected_cells >= 0
            library_mask = cell_mask & library_row_mask[rows]
            if np.any(library_mask):
                np.add.at(
                    library_sizes,
                    selected_cells[library_mask],
                    values[library_mask].astype(np.float64),
                )
            selected_features = row_map[rows]
            value_mask = cell_mask & (selected_features >= 0)
            if np.any(value_mask):
                np.add.at(
                    counts,
                    (
                        selected_features[value_mask],
                        selected_cells[value_mask],
                    ),
                    values[value_mask].astype(np.float64),
                )
        if tail.strip():
            triples = _parse_integer_block(tail + b"\n")
            parsed += len(triples)
            rows = triples[:, 0] - 1
            columns = triples[:, 1] - 1
            values = triples[:, 2]
            if (
                np.any(rows < 0)
                or np.any(rows >= row_count)
                or np.any(columns < 0)
                or np.any(columns >= column_count)
                or np.any(values <= 0)
            ):
                raise StressError("external Matrix Market coordinate is out of range")
            selected_cells = column_map[columns]
            cell_mask = selected_cells >= 0
            library_mask = cell_mask & library_row_mask[rows]
            if np.any(library_mask):
                np.add.at(
                    library_sizes,
                    selected_cells[library_mask],
                    values[library_mask].astype(np.float64),
                )
            selected_features = row_map[rows]
            value_mask = cell_mask & (selected_features >= 0)
            if np.any(value_mask):
                np.add.at(
                    counts,
                    (selected_features[value_mask], selected_cells[value_mask]),
                    values[value_mask].astype(np.float64),
                )
    if parsed != expected_entries or not np.all(library_sizes > 0):
        raise StressError("external Matrix Market entry or library-size closure changed")
    return counts, library_sizes, parsed


def _truth(
    counts: np.ndarray,
    library_sizes: np.ndarray,
    group_positions: dict[str, list[int]],
) -> dict[str, np.ndarray]:
    def mean_for(positions: list[int]) -> np.ndarray:
        index = np.asarray(positions, dtype=np.int64)
        values = counts[:, index] * (10000.0 / library_sizes[index])
        np.log1p(values, out=values)
        return np.mean(values, axis=1, dtype=np.float64)

    control = mean_for(group_positions["__control__"])
    return {
        symbol: mean_for(positions) - control
        for symbol, positions in group_positions.items()
        if symbol != "__control__"
    }


def _mse(prediction: np.ndarray, truth: np.ndarray) -> float:
    if prediction.shape != truth.shape or not np.isfinite(truth).all():
        raise StressError("external truth or prediction is invalid")
    return float(np.mean(np.square(prediction - truth), dtype=np.float64))


def _paired_bootstrap(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (7,) or not np.isfinite(array).all():
        raise StressError("external paired bootstrap requires seven finite values")
    rng = np.random.Generator(np.random.PCG64(0))
    positions = rng.integers(0, 7, size=(2000, 7), dtype=np.int64)
    means = np.mean(array[positions], axis=1, dtype=np.float64)
    low, high = np.quantile(means, [0.025, 0.975], method="linear")
    return {
        "estimate": float(np.mean(array, dtype=np.float64)),
        "low": float(low),
        "high": float(high),
        "unit": "external_target_condition",
        "method": "paired_percentile",
        "rng": "numpy.PCG64",
        "seed": 0,
        "replicates": 2000,
        "interval": [0.025, 0.975],
        "quantile_method": "linear",
    }


def _write_new(path: Path, data: bytes) -> None:
    if path.is_symlink() or os.path.lexists(path) or not path.parent.is_dir():
        raise StressError("output must be a new file under an existing directory")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def evaluate(
    *,
    protocol_path: Path,
    input_dir: Path,
    candidate_root: Path,
    comparator_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    protocol = _load_protocol(protocol_path)
    runtime = _verify_runtime(protocol)
    input_records = _checked_files(input_dir, protocol["external_dataset"]["files"], _INPUT_FILES)
    candidate = _load_model(candidate_root, protocol["candidate"], candidate=True)
    comparator = _load_model(comparator_root, protocol["comparator"], candidate=False)
    (
        candidate_features,
        candidate_targets,
        candidate_coefficients,
        candidate_intercept,
        candidate_seen_targets,
    ) = candidate
    (
        comparator_features,
        comparator_targets,
        comparator_coefficients,
        comparator_intercept,
        comparator_seen_targets,
    ) = comparator
    if candidate_features != comparator_features:
        raise StressError("candidate and comparator feature axes differ")
    targets = protocol["selection"]["targets"]
    requested_target_ids = {record["ensembl_id"] for record in targets}
    if not (
        requested_target_ids <= set(candidate_seen_targets) and requested_target_ids <= set(comparator_seen_targets)
    ):
        raise StressError("external target was not seen during frozen model training")
    candidate_predictions = _predictions(targets, candidate_targets, candidate_coefficients, candidate_intercept)
    comparator_predictions = _predictions(targets, comparator_targets, comparator_coefficients, comparator_intercept)

    dataset = protocol["external_dataset"]
    barcodes = _barcodes(
        input_dir / "GSM4367986_exp8.barcodes.tsv.gz",
        dataset["expected_barcode_rows"],
    )
    external_features, _external_symbols, gene_expression_rows = _features(
        input_dir / "GSM4367986_exp8.features.tsv.gz",
        dataset["expected_feature_rows"],
        dataset["expected_feature_type_counts"],
    )
    groups, cell_receipt = _selected_groups(
        input_dir / "GSM4367986_exp8.cell_identities.csv.gz",
        protocol["selection"],
        dataset["expected_cell_identity_rows"],
        set(candidate_seen_targets),
    )
    barcode_positions = {value: index for index, value in enumerate(barcodes)}
    selected_barcodes = [barcode for values in groups.values() for barcode in values]
    if any(value not in barcode_positions for value in selected_barcodes):
        raise StressError("selected metadata barcode is absent from the matrix axis")
    selected_columns = [barcode_positions[value] for value in selected_barcodes]
    selected_position = {barcode: index for index, barcode in enumerate(selected_barcodes)}
    group_positions = {symbol: [selected_position[barcode] for barcode in values] for symbol, values in groups.items()}
    external_position = {value: index for index, value in enumerate(external_features)}
    if any(value not in external_position for value in candidate_features):
        raise StressError("candidate feature is absent from the external matrix")
    feature_rows = [external_position[value] for value in candidate_features]
    if feature_rows != sorted(feature_rows):
        raise StressError("candidate feature relative order changed in the external matrix")
    counts, library_sizes, matrix_entries = _selected_counts(
        input_dir / "GSM4367986_exp8.matrix.mtx.gz",
        expected_shape=dataset["expected_matrix_shape"],
        expected_entries=dataset["expected_matrix_entries"],
        feature_rows=feature_rows,
        library_feature_rows=np.flatnonzero(gene_expression_rows).tolist(),
        selected_columns=selected_columns,
    )
    truths = _truth(counts, library_sizes, group_positions)

    per_target: list[dict[str, Any]] = []
    differences: list[float] = []
    candidate_losses: list[float] = []
    comparator_losses: list[float] = []
    for target in targets:
        symbol = target["symbol"]
        candidate_mse = _mse(candidate_predictions[symbol], truths[symbol])
        comparator_mse = _mse(comparator_predictions[symbol], truths[symbol])
        difference = candidate_mse - comparator_mse
        candidate_losses.append(candidate_mse)
        comparator_losses.append(comparator_mse)
        differences.append(difference)
        per_target.append(
            {
                "symbol": symbol,
                "ensembl_id": target["ensembl_id"],
                "cells": len(groups[symbol]),
                "candidate_mse": candidate_mse,
                "comparator_mse": comparator_mse,
                "candidate_minus_comparator_mse": difference,
                "truth_delta_sha256": hashlib.sha256(np.asarray(truths[symbol], dtype=">f8").tobytes()).hexdigest(),
                "candidate_prediction_sha256": hashlib.sha256(
                    np.asarray(candidate_predictions[symbol], dtype=">f8").tobytes()
                ).hexdigest(),
                "comparator_prediction_sha256": hashlib.sha256(
                    np.asarray(comparator_predictions[symbol], dtype=">f8").tobytes()
                ).hexdigest(),
            }
        )
    interval = _paired_bootstrap(differences)
    passed = interval["estimate"] < 0.0 and interval["high"] < 0.0
    result = {
        "schema_version": "praxis.golden-additive-gse146194-external-stress-result.v1",
        "record_role": "prospective_external_stress_result_not_p16_not_scientific_evidence",
        "protocol_sha256": protocol["identity"]["payload_sha256"],
        "evaluator_sha256": protocol["identity"]["evaluator_sha256"],
        "runtime": runtime,
        "input_files": input_records,
        "candidate": protocol["candidate"],
        "comparator": protocol["comparator"],
        "dataset": {
            "accession": dataset["accession"],
            "sample": dataset["sample"],
            "experiment": dataset["experiment"],
            "bioproject": dataset["bioproject"],
            "sra_project": dataset["sra_project"],
            "organism": dataset["organism"],
            "cell_line": dataset["cell_line"],
            "cell_identity_id": dataset["cell_identity_id"],
            "perturbation_system": dataset["perturbation_system"],
            "sample_time_after_infection_days": dataset["sample_time_after_infection_days"],
            "exact_P16_time_days": dataset["exact_P16_time_days"],
            "platform": dataset["platform"],
            "genome_build": dataset["genome_build"],
            "license": dataset["license"],
            "matrix_shape": dataset["expected_matrix_shape"],
            "matrix_entries": matrix_entries,
            "gene_expression_feature_count": int(np.sum(gene_expression_rows)),
            "guide_capture_feature_count": int(np.sum(~gene_expression_rows)),
            "selected_feature_count": len(feature_rows),
            **cell_receipt,
        },
        "preprocessing": protocol["preprocessing"],
        "primary_test": protocol["primary_test"],
        "decision_path_exposure": protocol["decision_path_exposure"],
        "metrics": {
            "per_target": per_target,
            "candidate_macro_mse": float(np.mean(candidate_losses, dtype=np.float64)),
            "comparator_macro_mse": float(np.mean(comparator_losses, dtype=np.float64)),
            "candidate_minus_comparator_macro_mse": interval["estimate"],
            "paired_percentile_ci95": interval,
            "external_stress_test_passed": passed,
        },
        "exposure_audit": {
            **protocol["exposure_audit"],
            "raw_matrix_bytes_received_by_evaluator": True,
            "matrix_expression_entries_decoded_during_frozen_evaluation": True,
            "external_condition_outcomes_computed_during_frozen_evaluation": True,
            "external_expression_used_only_for_this_frozen_stress_evaluation": True,
            "candidate_or_comparator_training_tuning_or_calibration_on_external": False,
            "golden_test_expression_used": False,
            "golden_test_outcomes_used": False,
        },
        "states": {
            "external_stress_test_passed": passed,
            "p16_exact_external_gate_satisfied": False,
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
            "registry_or_default_route_changed": False,
        },
        "claim_ceiling_reasons": protocol["claim_ceiling"]["reasons"],
    }
    _write_new(output_path, _canonical_bytes(result) + b"\n")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=_DEFAULT_PROTOCOL)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--comparator-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = evaluate(
        protocol_path=args.protocol,
        input_dir=args.input_dir,
        candidate_root=args.candidate_root,
        comparator_root=args.comparator_root,
        output_path=args.output,
    )
    metrics = result["metrics"]
    print(f"candidate_macro_mse={metrics['candidate_macro_mse']:.12g}")
    print(f"comparator_macro_mse={metrics['comparator_macro_mse']:.12g}")
    print(
        "candidate_minus_comparator_ci95="
        f"[{metrics['paired_percentile_ci95']['low']:.12g},"
        f"{metrics['paired_percentile_ci95']['high']:.12g}]"
    )
    print(f"external_stress_test_passed={str(metrics['external_stress_test_passed']).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

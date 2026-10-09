#!/usr/bin/env python3
"""Build a local GEARS candidate from a reconstructed Golden-train-only input."""

from __future__ import annotations

import argparse
import csv
import ctypes
import errno
import fcntl
import hashlib
import importlib
import io
import json
import math
import os
import pickle
import pickletools
import secrets
import shutil
import site
import stat
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

_PROTOCOL = Path(__file__).parents[1] / "data/golden/norman_2019/gears_train_only_protocol.json"
_PARTITIONS = ("train", "validation", "test")
_CONTROL = "ctrl"
_RANK_PREFIX = b"praxis-gears-internal-validation-v1\0"
_SANDBOX = Path("/usr/bin/sandbox-exec")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CandidateBuildError("candidate protocol contains duplicate JSON keys")
        value[key] = item
    return value


class CandidateBuildError(ValueError):
    """Fail-closed candidate-build error."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise CandidateBuildError("expected a regular file")
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise CandidateBuildError("file changed while hashing")
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _file_record(path: Path, *, single_link: bool = False) -> dict[str, Any]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or (single_link and info.st_nlink != 1):
        raise CandidateBuildError("output inventory contains an unsafe file")
    digest = _sha256(path)
    after = path.lstat()
    if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise CandidateBuildError("output inventory changed while hashing")
    return {"size_bytes": info.st_size, "sha256": digest}


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
    if value.get("schema_version") != "praxis.golden-gears-train-only-protocol.v1":
        raise CandidateBuildError("unsupported candidate protocol")
    expected = value["identity"]["payload_sha256"]
    copy = json.loads(_canonical_bytes(value))
    copy["identity"]["payload_sha256"] = None
    if expected != _fingerprint(copy):
        raise CandidateBuildError("candidate protocol payload hash changed")
    if value["identity"]["builder_sha256"] != _sha256(Path(__file__)):
        raise CandidateBuildError("candidate builder differs from the frozen protocol")
    return value


def _regular_bytes(path: Path, *, size: int, sha256: str, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CandidateBuildError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size != size:
            raise CandidateBuildError(f"{label} identity mismatch")
        chunks = []
        remaining = size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(payload) != size
            or hashlib.sha256(payload).hexdigest() != sha256
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        ):
            raise CandidateBuildError(f"{label} identity mismatch")
        return payload
    finally:
        os.close(descriptor)


class _PrimitiveUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        raise CandidateBuildError("unsafe global in gene2go pickle")


class _NumpyArrayUnpickler(pickle.Unpickler):
    _ALLOWED = {
        ("numpy.core.multiarray", "_reconstruct"),
        ("numpy._core.multiarray", "_reconstruct"),
        ("numpy", "ndarray"),
        ("numpy", "dtype"),
    }

    def find_class(self, module: str, name: str) -> Any:
        if (module, name) not in self._ALLOWED:
            raise CandidateBuildError("unsafe global in essential-gene pickle")
        return super().find_class(module, name)


def _validate_pickle(payload: bytes, kind: str) -> Any:
    forbidden = {"EXT1", "EXT2", "EXT4", "INST", "OBJ", "PERSID", "BINPERSID"}
    try:
        operations = list(pickletools.genops(payload))
    except (ValueError, pickle.UnpicklingError) as exc:
        raise CandidateBuildError(f"{kind} pickle is malformed") from exc
    if not operations or operations[-1][0].name != "STOP" or operations[-1][2] != len(payload) - 1:
        raise CandidateBuildError(f"{kind} pickle has trailing or incomplete data")
    if any(operation.name in forbidden for operation, _argument, _position in operations):
        raise CandidateBuildError(f"unsafe opcode in {kind} pickle")
    names = [operation.name for operation, _argument, _position in operations]
    if kind == "gene2go":
        if any(name in {"GLOBAL", "STACK_GLOBAL", "REDUCE", "BUILD", "NEWOBJ", "NEWOBJ_EX"} for name in names):
            raise CandidateBuildError("unsafe opcode in gene2go pickle")
    else:
        if (
            any(name in {"NEWOBJ", "NEWOBJ_EX"} for name in names)
            or sum(name == "REDUCE" for name in names) != 2
            or sum(name == "BUILD" for name in names) != 2
        ):
            raise CandidateBuildError("essential-gene pickle opcode schema changed")
    try:
        if kind == "gene2go":
            value = _PrimitiveUnpickler(io.BytesIO(payload)).load()
            if (
                type(value) is not dict
                or not value
                or any(
                    type(key) is not str
                    or not key
                    or type(items) is not set
                    or not items
                    or any(type(item) is not str or not item for item in items)
                    for key, items in value.items()
                )
            ):
                raise CandidateBuildError("gene2go pickle schema changed")
        else:
            value = _NumpyArrayUnpickler(io.BytesIO(payload)).load()
            import numpy as np

            array = np.asarray(value)
            strings = array.tolist()
            if (
                array.ndim != 1
                or not strings
                or any(type(item) is not str or not item for item in strings)
                or len(strings) != len(set(strings))
            ):
                raise CandidateBuildError("essential-gene pickle schema changed")
    except CandidateBuildError:
        raise
    except Exception as exc:
        raise CandidateBuildError(f"{kind} pickle schema changed") from exc
    return value


def _validate_go_tar(payload: bytes, record: dict[str, Any], target: Path) -> dict[str, Any]:
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            members = archive.getmembers()
            if [member.name for member in members] != record["allowed_members"]:
                raise CandidateBuildError("GO archive member allowlist changed")
            directory, csv_member = members
            if not directory.isdir() or not csv_member.isfile() or csv_member.size != record["csv"]["size_bytes"]:
                raise CandidateBuildError("GO archive member identity changed")
            stream = archive.extractfile(csv_member)
            if stream is None:
                raise CandidateBuildError("GO CSV is unavailable")
            csv_path = target / "go_essential_all.csv"
            descriptor = os.open(csv_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            digest = hashlib.sha256()
            size = 0
            prefix = b""
            with os.fdopen(descriptor, "wb") as output:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                    if b"\n" not in prefix:
                        prefix += chunk
                output.flush()
                os.fsync(output.fileno())
            if size != record["csv"]["size_bytes"] or digest.hexdigest() != record["csv"]["sha256"]:
                raise CandidateBuildError("GO CSV identity changed")
            if prefix.splitlines()[0].decode("utf-8") != ",".join(record["csv"]["header"]):
                raise CandidateBuildError("GO CSV schema changed")
            sources: set[str] = set()
            targets: set[str] = set()
            self_edges: set[str] = set()
            rows = 0
            minimum = float("inf")
            maximum = float("-inf")
            with csv_path.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames != record["csv"]["header"]:
                    raise CandidateBuildError("GO CSV schema changed")
                for row in reader:
                    source = row["source"]
                    target_gene = row["target"]
                    try:
                        importance = float(row["importance"])
                    except (TypeError, ValueError) as exc:
                        raise CandidateBuildError("GO CSV importance is invalid") from exc
                    if not source or not target_gene or not math.isfinite(importance):
                        raise CandidateBuildError("GO CSV row is invalid")
                    sources.add(source)
                    targets.add(target_gene)
                    if source == target_gene:
                        self_edges.add(source)
                    rows += 1
                    minimum = min(minimum, importance)
                    maximum = max(maximum, importance)
            expected = record["csv"]
            if (
                rows != expected["data_rows"]
                or len(sources) != expected["unique_source_genes"]
                or len(targets) != expected["unique_target_genes"]
                or len(self_edges) != expected["self_edge_genes"]
                or minimum < expected["minimum_importance_at_least"]
                or maximum > expected["maximum_importance_at_most"]
            ):
                raise CandidateBuildError("GO CSV semantic identity changed")
            return {
                "sources": sources,
                "targets": targets,
                "self_edges": self_edges,
                "data_rows": rows,
                "minimum_importance": minimum,
                "maximum_importance": maximum,
            }
    except (tarfile.TarError, OSError) as exc:
        raise CandidateBuildError("GO archive is invalid") from exc


def _wheelhouse_identity(root: Path) -> dict[str, Any]:
    if root.is_symlink() or not root.is_dir():
        raise CandidateBuildError("wheelhouse must be a regular directory")
    records = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if path.is_symlink() or not path.is_file() or not path.name.endswith(".whl") or path.name.startswith("._"):
            raise CandidateBuildError("wheelhouse contains an unsafe or unknown entry")
        identity = _file_record(path)
        records.append({"filename": path.name, **identity})
    envelope = {
        "schema_version": "praxis.gears-wheelhouse.v1",
        "target": "cp313-macos-arm64",
        "files": records,
    }
    return {
        "regular_wheel_count": len(records),
        "total_size_bytes": sum(record["size_bytes"] for record in records),
        "manifest_sha256": _fingerprint(envelope),
    }


def _validate_additive(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    if root.is_symlink() or not root.is_dir():
        raise CandidateBuildError("additive model must be a regular directory")
    expected = protocol["candidate"]["fallback"]["assets"]
    entries = [path for path in root.iterdir() if not path.name.startswith("._")]
    if {path.name for path in entries} != set(expected):
        raise CandidateBuildError("additive model inventory changed")
    payloads = {
        name: _regular_bytes(root / name, size=record["size_bytes"], sha256=record["sha256"], label=f"additive {name}")
        for name, record in expected.items()
    }
    try:
        metadata = json.loads(
            payloads["baseline.json"],
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                CandidateBuildError("additive metadata contains non-finite JSON")
            ),
        )
        if not isinstance(metadata, dict):
            raise CandidateBuildError("additive metadata schema changed")
        import numpy as np

        coefficients = np.load(io.BytesIO(payloads["linear_coefficients.npy"]), allow_pickle=False)
        intercept = np.load(io.BytesIO(payloads["linear_intercept.npy"]), allow_pickle=False)
        target_ids = metadata.get("target_ids")
        feature_ids = metadata.get("feature_ids")
        arrays = metadata.get("arrays")
        if not (
            metadata.get("schema_version") == "vc.golden-baseline.v1"
            and metadata.get("baseline") == "additive_linear"
            and metadata.get("model_name") == protocol["candidate"]["fallback"]["model"]
            and isinstance(target_ids, list)
            and isinstance(feature_ids, list)
            and _fingerprint(target_ids) == metadata.get("target_ids_sha256")
            and _fingerprint(feature_ids) == protocol["pack"]["feature_ids_sha256"]
            and isinstance(arrays, dict)
            and arrays.get("linear_coefficients.npy", {}).get("sha256") == expected["linear_coefficients.npy"]["sha256"]
            and arrays.get("linear_intercept.npy", {}).get("sha256") == expected["linear_intercept.npy"]["sha256"]
            and coefficients.shape == (len(target_ids), len(feature_ids))
            and intercept.shape == (len(feature_ids),)
            and coefficients.dtype == np.dtype("float64")
            and intercept.dtype == np.dtype("float64")
            and np.isfinite(coefficients).all()
            and np.isfinite(intercept).all()
        ):
            raise CandidateBuildError("additive model schema changed")
    except CandidateBuildError:
        raise
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CandidateBuildError("additive model schema changed") from exc
    return {name: {"size_bytes": record["size_bytes"], "sha256": record["sha256"]} for name, record in expected.items()}


def _canonical_targets(condition: str) -> tuple[str, ...]:
    targets = tuple(sorted(value for value in condition.split("+") if value != "ctrl"))
    if not targets or len(targets) not in {1, 2} or len(targets) != len(set(targets)):
        raise CandidateBuildError("condition target grammar changed")
    return targets


def _child_label(targets: tuple[str, ...]) -> str:
    return f"{targets[0]}+ctrl" if len(targets) == 1 else "+".join(targets)


def _rank(targets: tuple[str, ...], seed: int) -> bytes:
    return hashlib.sha256(_RANK_PREFIX + str(seed).encode() + b"\0" + _canonical_bytes(list(targets))).digest()


def _split_audit(obs, protocol: dict[str, Any]) -> tuple[dict[str, Any], dict[str, tuple[str, ...]]]:
    condition_field = protocol["pack"]["condition_field"]
    split_field = protocol["pack"]["split_field"]
    expected = protocol["contamination_contract"]["expected"]
    conditions: dict[str, set[str]] = {}
    tuples: dict[str, set[tuple[str, ...]]] = {}
    targets: dict[str, set[str]] = {}
    mapping: dict[str, tuple[str, ...]] = {}
    rows: dict[str, int] = {}
    control_rows: dict[str, int] = {}
    singles: dict[str, int] = {}
    combinations: dict[str, int] = {}
    for partition in _PARTITIONS:
        frame = obs.loc[obs[split_field].eq(partition)]
        rows[partition] = len(frame)
        control_id = protocol["pack"]["control_condition_ids"][partition]
        control_rows[partition] = int(frame[condition_field].eq(control_id).sum())
        noncontrol = {str(value) for value in frame.loc[~frame[condition_field].eq(control_id), condition_field]}
        conditions[partition] = noncontrol
        tuple_set = set()
        for condition in noncontrol:
            canonical = _canonical_targets(condition)
            mapping[condition] = canonical
            tuple_set.add(canonical)
        tuples[partition] = tuple_set
        targets[partition] = {target for item in tuple_set for target in item}
        singles[partition] = sum(len(mapping[condition]) == 1 for condition in noncontrol)
        combinations[partition] = sum(len(mapping[condition]) == 2 for condition in noncontrol)
    if (
        rows != expected["rows"]
        or control_rows != expected["controls"]
        or {key: len(value) for key, value in conditions.items()} != expected["noncontrol_conditions"]
        or singles != expected["single_conditions"]
        or combinations != expected["combination_conditions"]
        or any(_fingerprint(sorted(conditions[key])) != expected["condition_set_sha256"][key] for key in _PARTITIONS)
        or any(
            len(tuples[key]) != expected["canonical_symbol_target_tuple_set"][key]["count"]
            or _fingerprint(sorted(map(list, tuples[key])))
            != expected["canonical_symbol_target_tuple_set"][key]["sha256"]
            for key in _PARTITIONS
        )
    ):
        raise CandidateBuildError("Golden split identity changed")
    overlaps = {}
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        condition_overlap = sorted(conditions[left] & conditions[right])
        tuple_overlap = sorted(map(list, tuples[left] & tuples[right]))
        if condition_overlap or tuple_overlap:
            raise CandidateBuildError("Golden split contamination detected")
        intersection = sorted(targets[left] & targets[right])
        overlaps[f"{left}_{right}"] = {
            "condition_ids": [],
            "canonical_target_tuples": [],
            "individual_target_count": len(intersection),
            "individual_targets_sha256": _fingerprint(intersection),
        }
    return {
        "status": "passed",
        "rows": rows,
        "controls": control_rows,
        "noncontrol_conditions": {key: len(value) for key, value in conditions.items()},
        "canonical_target_tuples": {key: len(value) for key, value in tuples.items()},
        "individual_target_overlap_is_not_leakage": True,
        "pairwise": overlaps,
    }, mapping


def _graph_scope_audit(
    obs,
    protocol: dict[str, Any],
    condition_targets: dict[str, tuple[str, ...]],
    eligible_targets: set[str],
) -> dict[str, Any]:
    condition_field = protocol["pack"]["condition_field"]
    split_field = protocol["pack"]["split_field"]
    observed: dict[str, dict[str, Any]] = {}
    for partition in _PARTITIONS:
        frame = obs.loc[obs[split_field].eq(partition)]
        control_id = protocol["pack"]["control_condition_ids"][partition]
        raw = sorted(
            {str(value) for value in frame.loc[~frame[condition_field].eq(control_id), condition_field].tolist()}
        )
        unsupported = sorted(
            condition for condition in raw if not set(condition_targets[condition]).issubset(eligible_targets)
        )
        native = sorted(set(raw).difference(unsupported))
        native_tuples = sorted({condition_targets[condition] for condition in native})
        unsupported_targets = sorted(
            {
                target
                for condition in unsupported
                for target in condition_targets[condition]
                if target not in eligible_targets
            }
        )
        unsupported_mask = frame[condition_field].astype(str).isin(unsupported)
        unsupported_ids = [str(value) for value in frame.index[unsupported_mask].tolist()]
        unsupported_condition_rows = {
            condition: int(count)
            for condition, count in frame.loc[unsupported_mask, condition_field]
            .astype(str)
            .value_counts()
            .sort_index()
            .items()
        }
        observed[partition] = {
            "unsupported_targets": unsupported_targets,
            "unsupported_conditions": unsupported,
            "unsupported_rows": len(unsupported_ids),
            "unsupported_condition_rows": unsupported_condition_rows,
            "unsupported_observation_ids_source_order_sha256": _fingerprint(unsupported_ids),
            "unsupported_observation_ids_sorted_sha256": _fingerprint(sorted(unsupported_ids)),
            "native_raw_conditions": len(native),
            "native_raw_condition_ids_sha256": _fingerprint(native),
            "native_canonical_conditions": len(native_tuples),
            "native_canonical_conditions_sha256": _fingerprint([list(item) for item in native_tuples]),
        }
    fallback = protocol["candidate"]["fallback"]
    train_expected = fallback["excluded_from_native_training"]
    train = observed["train"]
    test = observed["test"]
    native = protocol["training"]["native_input"]
    if (
        train["unsupported_targets"] != fallback["unsupported_train_targets"]["symbols"]
        or _fingerprint(train["unsupported_targets"]) != fallback["unsupported_train_targets"]["sha256"]
        or train["unsupported_conditions"] != sorted(train_expected["conditions"])
        or train["unsupported_condition_rows"] != train_expected["conditions"]
        or _fingerprint(train["unsupported_conditions"]) != train_expected["condition_ids_sha256"]
        or train["unsupported_rows"] != train_expected["rows"]
        or train["unsupported_observation_ids_source_order_sha256"]
        != native["excluded_observation_ids"]["source_order_sha256"]
        or train["unsupported_observation_ids_sorted_sha256"] != native["excluded_observation_ids"]["sorted_sha256"]
        or test["unsupported_targets"] != fallback["unsupported_test_targets"]["symbols"]
        or _fingerprint(test["unsupported_targets"]) != fallback["unsupported_test_targets"]["sha256"]
        or test["unsupported_conditions"] != fallback["expected_test_fallback_conditions"]
        or _fingerprint(test["unsupported_conditions"]) != fallback["expected_test_fallback_condition_ids_sha256"]
        or test["unsupported_rows"] != fallback["expected_test_fallback_rows"]
        or test["unsupported_observation_ids_source_order_sha256"]
        != fallback["expected_test_fallback_observation_ids_source_order_sha256"]
        or test["unsupported_observation_ids_sorted_sha256"]
        != fallback["expected_test_fallback_observation_ids_sorted_sha256"]
        or test["native_raw_conditions"] != fallback["expected_test_native_raw_conditions"]
        or test["native_raw_condition_ids_sha256"] != fallback["expected_test_native_raw_condition_ids_sha256"]
        or test["native_canonical_conditions"] != fallback["expected_test_native_canonical_conditions"]
        or test["native_canonical_conditions_sha256"] != fallback["expected_test_native_canonical_conditions_sha256"]
        or observed["validation"]["unsupported_conditions"]
    ):
        raise CandidateBuildError("GEARS graph scope identity changed")
    return observed


def _reconstruct_train_input(
    pack_asset: str,
    target: Path,
    protocol: dict[str, Any],
    gene2go: dict[str, Any],
    essential_genes: set[str],
):
    try:
        import anndata
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise CandidateBuildError("anndata runtime is unavailable") from exc
    source = anndata.read_h5ad(pack_asset, backed="r")
    try:
        if list(source.shape) != protocol["pack"]["shape"]:
            raise CandidateBuildError("Golden expression shape changed")
        obs = source.obs.copy()
        symbols = [str(value) for value in source.var[protocol["pack"]["feature_symbol_field"]].tolist()]
        feature_ids = [str(value) for value in source.var_names.tolist()]
        if (
            _fingerprint(feature_ids) != protocol["pack"]["feature_ids_sha256"]
            or _fingerprint(symbols) != protocol["pack"]["feature_symbols_sha256"]
        ):
            raise CandidateBuildError("Golden feature identity changed")
        audit, condition_targets = _split_audit(obs, protocol)
        eligible_targets = set(gene2go).intersection(essential_genes)
        expected_eligibility = protocol["candidate"]["fallback"]["eligibility_gene_set"]
        if (
            len(eligible_targets) != expected_eligibility["count"]
            or _fingerprint(sorted(eligible_targets)) != expected_eligibility["sha256"]
        ):
            raise CandidateBuildError("GEARS eligibility gene set changed")
        graph_scope = _graph_scope_audit(obs, protocol, condition_targets, eligible_targets)
        train_mask = obs[protocol["pack"]["split_field"]].eq("train").to_numpy()
        train_ids = [str(value) for value in obs.index[train_mask].tolist()]
        expected_train_ids = protocol["contamination_contract"]["expected"]["train_observation_ids_source_order_sha256"]
        if _fingerprint(train_ids) != expected_train_ids:
            raise CandidateBuildError("Golden train observation identity changed")
        condition_values = obs[protocol["pack"]["condition_field"]].astype(str).to_numpy()
        native_mask = train_mask & np.asarray(
            [
                condition in protocol["pack"]["control_condition_ids"].values()
                or set(_canonical_targets(condition)).issubset(eligible_targets)
                for condition in condition_values
            ]
        )
        positions = np.flatnonzero(native_mask)
        native_ids = [str(value) for value in obs.index[positions].tolist()]
        native = protocol["training"]["native_input"]
        if (
            len(positions) != native["rows"]
            or _fingerprint(native_ids) != native["observation_ids_source_order_sha256"]
        ):
            raise CandidateBuildError("native train observation identity changed")
        child_conditions = []
        for condition in condition_values[positions]:
            if condition == protocol["pack"]["control_condition_ids"]["train"]:
                child_conditions.append(_CONTROL)
            else:
                child_conditions.append(_child_label(condition_targets[condition]))
        canonical_labels = sorted(set(child_conditions))
        if _fingerprint(canonical_labels) != native["canonical_child_labels_including_control_sha256"]:
            raise CandidateBuildError("native condition identity changed")
        supported_targets = sorted(
            {
                target
                for condition in child_conditions
                if condition != _CONTROL
                for target in _canonical_targets(condition)
            }
        )
        if (
            len(supported_targets) != native["supported_symbol_targets"]["count"]
            or _fingerprint(supported_targets) != native["supported_symbol_targets"]["sha256"]
        ):
            raise CandidateBuildError("native target identity changed")
        absent = sorted(set(supported_targets).difference(eligible_targets))
        if absent:
            raise CandidateBuildError("native train target is absent from the frozen GO graph")
        supported = sorted(
            {_child_label(_canonical_targets(condition)) for condition in child_conditions if condition != _CONTROL}
        )
        ranked = sorted(
            (_canonical_targets(condition) for condition in supported),
            key=lambda item: (_rank(item, protocol["training"]["preprocessing_seed"]), item),
        )
        n_validation = math.ceil(len(ranked) * 0.1)
        validation_targets = ranked[:n_validation]
        train_targets = ranked[n_validation:]
        train_labels = sorted([_CONTROL, *(_child_label(item) for item in train_targets)])
        validation_labels = sorted(_child_label(item) for item in validation_targets)
        internal = protocol["training"]["internal_validation"]
        train_id_set = set(train_labels)
        validation_id_set = set(validation_labels)
        internal_train_ids = [
            native_ids[index] for index, label in enumerate(child_conditions) if label in train_id_set
        ]
        internal_validation_ids = [
            native_ids[index] for index, label in enumerate(child_conditions) if label in validation_id_set
        ]
        if (
            _fingerprint([list(item) for item in validation_targets])
            != internal["validation_rank_order_target_lists_sha256"]
            or _fingerprint([list(item) for item in train_targets]) != internal["train_rank_order_target_lists_sha256"]
            or _fingerprint(validation_labels) != internal["validation_canonical_labels_sha256"]
            or _fingerprint(train_labels) != internal["train_canonical_labels_with_control_sha256"]
            or len(internal_train_ids) != internal["train_rows"]
            or _fingerprint(internal_train_ids) != internal["train_observation_ids_source_order_sha256"]
            or len(internal_validation_ids) != internal["validation_rows"]
            or _fingerprint(internal_validation_ids) != internal["validation_observation_ids_source_order_sha256"]
        ):
            raise CandidateBuildError("internal validation identity changed")
        child_obs = pd.DataFrame(
            {"condition": list(map(str, child_conditions)), "cell_type": ["K562"] * len(positions)},
            index=pd.Index(native_ids, dtype="object"),
        )
        child_var = pd.DataFrame({"gene_name": list(map(str, symbols))}, index=pd.Index(feature_ids, dtype="object"))
        child = anndata.AnnData(X=source.X[positions].copy(), obs=child_obs, var=child_var)
        if child.uns or child.obsm or child.varm or child.layers or child.raw is not None:
            raise CandidateBuildError("derived H5AD contains undeclared containers")
        child.write_h5ad(target)
    finally:
        source.file.close()
    return audit, {
        "native_rows": len(native_ids),
        "native_observation_ids_sha256": _fingerprint(native_ids),
        "feature_count": len(feature_ids),
        "native_target_count": len(supported_targets),
        "native_targets_sha256": _fingerprint(supported_targets),
        "internal_train_conditions": train_labels,
        "internal_validation_conditions": validation_labels,
        "graph_scope": graph_scope,
    }


def _verify_pack(pack_root: Path, protocol: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    raw_root = pack_root
    if raw_root.is_symlink():
        raise CandidateBuildError("Pack root must not be a symlink")
    try:
        pack_root = raw_root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise CandidateBuildError("Pack root is unavailable") from exc
    if not pack_root.is_dir():
        raise CandidateBuildError("Pack root must be a directory")
    import yaml

    manifest_record = protocol["pack"]["manifest"]
    manifest_bytes = _regular_bytes(
        pack_root / manifest_record["filename"],
        size=manifest_record["size_bytes"],
        sha256=manifest_record["sha256"],
        label="Golden Pack manifest",
    )
    try:
        manifest = yaml.safe_load(manifest_bytes)
    except yaml.YAMLError as exc:
        raise CandidateBuildError("Golden Pack manifest is invalid") from exc
    expression_records = [
        item for item in manifest.get("assets", []) if isinstance(item, dict) and item.get("id") == "expression"
    ]
    if (
        manifest.get("pack_id") != protocol["pack"]["pack_id"]
        or manifest.get("pack_version") != protocol["pack"]["pack_version"]
        or len(expression_records) != 1
        or expression_records[0].get("path") != protocol["pack"]["expression_asset"]
        or expression_records[0].get("sha256") != protocol["pack"]["expression_sha256"]
        or expression_records[0].get("size_bytes") != protocol["pack"]["expression_size_bytes"]
    ):
        raise CandidateBuildError("Golden Pack manifest identity changed")
    contract_record = protocol["pack"]["golden_contract"]
    _regular_bytes(
        pack_root / contract_record["filename"],
        size=contract_record["size_bytes"],
        sha256=contract_record["sha256"],
        label="Golden contract",
    )
    asset = pack_root / protocol["pack"]["expression_asset"]
    if asset.is_symlink() or not asset.is_file():
        raise CandidateBuildError("Golden expression must be a regular non-symlink file")
    info = asset.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_size != protocol["pack"]["expression_size_bytes"]
        or _sha256(asset) != protocol["pack"]["expression_sha256"]
    ):
        raise CandidateBuildError("Golden expression identity changed")
    return asset, {
        "pack_id": protocol["pack"]["pack_id"],
        "pack_version": protocol["pack"]["pack_version"],
        "pack_fingerprint": protocol["pack"]["pack_fingerprint"],
        "expression_sha256": protocol["pack"]["expression_sha256"],
        "expression_size_bytes": protocol["pack"]["expression_size_bytes"],
    }


def _runtime_probe(python: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    package_names = list(protocol["runtime_environment"]["packages"])
    package_literal = repr(package_names)
    code = f"""import hashlib,json,platform,sysconfig
from importlib.metadata import version
from pathlib import Path
import dcor
import gears
root=Path(gears.__file__).parent
records=[]
for path in sorted(root.glob('*.py')):
 data=path.read_bytes()
 records.append({{'path':'gears/'+path.name,'size_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}})
packages={package_literal}
source_hash=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
out={{
 'python':platform.python_version(),
 'platform_system':platform.system(),
 'platform_machine':platform.machine(),
 'sysconfig_platform':sysconfig.get_platform(),
 'packages':{{name:version(name) for name in packages}},
 'gears_source_manifest_sha256':source_hash,
}}
print(json.dumps(out,sort_keys=True,separators=(',',':')))"""
    result = subprocess.run(
        [str(python), "-c", code],
        capture_output=True,
        check=False,
        text=True,
        env=_child_env(),
    )
    try:
        observed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CandidateBuildError("GEARS runtime probe failed") from exc
    expected = protocol["runtime_environment"]
    if (
        result.returncode != 0
        or observed["python"] != expected["python"]
        or observed["platform_system"] != expected["platform_system"]
        or observed["platform_machine"] != expected["platform_machine"]
        or observed["sysconfig_platform"] != expected["sysconfig_platform"]
        or observed["packages"] != expected["packages"]
        or observed["gears_source_manifest_sha256"]
        != protocol["candidate"]["implementation"]["installed_source_manifest_sha256"]
    ):
        raise CandidateBuildError("GEARS runtime identity changed")
    return observed


def _child_env(*, staging: Path | None = None) -> dict[str, str]:
    environment = {"PATH": os.defpath, "LC_ALL": "C", "LANG": "C", "TZ": "UTC", "HOME": "/nonexistent"}
    environment.update(
        {
            "NUMBA_THREADING_LAYER": "workqueue",
            "MPLBACKEND": "Agg",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
        }
    )
    if staging is not None:
        matplotlib_root = staging / ".matplotlib"
        matplotlib_root.mkdir(mode=0o700, exist_ok=True)
        environment["MPLCONFIGDIR"] = str(matplotlib_root)
    return environment


def _validate_parent_environment(protocol: dict[str, Any]) -> None:
    boundary = protocol["runtime_environment"]
    for name, value in boundary["required_environment"].items():
        if os.environ.get(name) != value:
            raise CandidateBuildError(f"required parent environment is not frozen: {name}")
    if any(name in os.environ for name in boundary["forbidden_environment"]):
        raise CandidateBuildError("forbidden parent environment is present")
    if site.ENABLE_USER_SITE:
        raise CandidateBuildError("parent user site-packages must be disabled")


def _validate_parent_module_origins(runtime: dict[str, Any]) -> None:
    from importlib.metadata import version

    prefix = Path(sys.prefix).resolve(strict=True)
    modules = {
        "anndata": "anndata",
        "h5py": "h5py",
        "numpy": "numpy",
        "pandas": "pandas",
        "PyYAML": "yaml",
    }
    for distribution, module_name in modules.items():
        module = importlib.import_module(module_name)
        origin = getattr(module, "__file__", None)
        if (
            version(distribution) != runtime["packages"][distribution]
            or not isinstance(origin, str)
            or not Path(origin).resolve(strict=True).is_relative_to(prefix)
        ):
            raise CandidateBuildError(f"parent module origin is outside the frozen runtime: {module_name}")


def _run_gears(
    python: Path,
    staging: Path,
    split: dict[str, Any],
    protocol: dict[str, Any],
    *,
    seed: int,
    epochs: int,
    batch_size: int,
) -> dict[str, Any]:
    job = {
        "input_h5ad": "input/native_train_only.h5ad",
        "gears_root": "gears-data",
        "model_output": f"models/seed-{seed}",
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
        "split": {"train": split["internal_train_conditions"], "val": split["internal_validation_conditions"]},
        "model": protocol["training"]["model"],
    }
    job_path = staging / "job.json"
    job_path.write_bytes(_canonical_bytes(job))
    # The child program is deliberately kept as inert data in this parent module.
    code = r"""
import json,os,random,sys
from pathlib import Path
root=Path.cwd(); job=json.loads((root/'job.json').read_text())
for value in (job['input_h5ad'],job['gears_root'],job['model_output']):
 p=Path(value)
 if p.is_absolute() or '..' in p.parts: raise ValueError('unsafe child path')
import dcor
import numpy as np, pandas as pd, torch
pd.Series.nonzero=lambda self:self.to_numpy().nonzero()
from gears import GEARS,PertData
seed=job['seed']
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
torch.use_deterministic_algorithms(True)
torch.set_num_threads(1); torch.set_num_interop_threads(1)
import anndata
adata=anndata.read_h5ad(root/job['input_h5ad'])
pd_=PertData(str(root/job['gears_root']))
random.seed(0); np.random.seed(0); torch.manual_seed(0)
pd_.new_data_process('norman_golden_train_only',adata=adata,skip_calc_de=False)
pd_.split='no_test'; pd_.seed=0; pd_.train_gene_set_size=None
pd_.set2conditions=job['split']
pd_.get_dataloader(batch_size=job['batch_size'])
if 'test_loader' in pd_.dataloader: raise RuntimeError('test loader forbidden')
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
g=GEARS(pd_,device='cpu',weight_bias_track=False)
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
m=job['model']
g.model_initialize(
 hidden_size=m['hidden_size'],
 num_go_gnn_layers=m['num_go_gnn_layers'],
 num_gene_gnn_layers=m['num_gene_gnn_layers'],
 decoder_hidden_size=m['decoder_hidden_size'],
 num_similar_genes_go_graph=m['num_similar_genes_go_graph'],
 num_similar_genes_co_express_graph=m['num_similar_genes_co_express_graph'],
 coexpress_threshold=m['coexpress_threshold'], uncertainty=m['uncertainty'],
 uncertainty_reg=m['uncertainty_reg'], direction_lambda=m['direction_lambda'],
 no_perturb=m['no_perturb'],
)
g.train(epochs=job['epochs'],lr=m['learning_rate'],weight_decay=m['weight_decay'])
out=root/job['model_output']; out.mkdir(parents=True); g.save_model(str(out))
print(json.dumps({'status':'completed','seed':seed,'epochs':job['epochs'],'test_loader_present':False},sort_keys=True,separators=(',',':')))
"""
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise CandidateBuildError("network-denying child sandbox is unavailable")
    command = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)", str(python), "-c", code]
    result = subprocess.run(
        command,
        cwd=staging,
        env=_child_env(staging=staging),
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise CandidateBuildError("GEARS child failed")
    try:
        receipt = json.loads(result.stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise CandidateBuildError("GEARS child receipt is invalid") from exc
    receipt["stdout_sha256"] = hashlib.sha256(result.stdout.encode()).hexdigest()
    receipt["stderr_sha256"] = hashlib.sha256(result.stderr.encode()).hexdigest()
    return receipt


def _publish(source: Path, target: Path, *, parent_fd: int) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        operation = getattr(libc, "renameatx_np", None)
        flag = 0x00000004
    elif sys.platform.startswith("linux"):
        operation = getattr(libc, "renameat2", None)
        flag = 1
    else:
        operation = None
        flag = 0
    if operation is None:
        raise CandidateBuildError("atomic no-replace output is unavailable")
    operation.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    operation.restype = ctypes.c_int
    if operation(parent_fd, os.fsencode(source.name), parent_fd, os.fsencode(target.name), flag) != 0:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise CandidateBuildError("output must be write-new")
        raise CandidateBuildError("candidate output publication failed") from OSError(error, os.strerror(error))


def _validated_output_parent(output: Path) -> tuple[Path, int]:
    if output.is_absolute():
        current = Path(output.anchor)
        parts = output.parts[1:-1]
        descriptor = os.open(current, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    else:
        current = Path.cwd()
        parts = output.parts[:-1]
        descriptor = os.open(current, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        for part in parts:
            if part in {"", ".", ".."}:
                raise CandidateBuildError("output path is unsafe")
            next_descriptor = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
            current = current / part
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise CandidateBuildError("output parent must be private and operator-owned")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise CandidateBuildError("output parent is already in use") from exc
        return current, descriptor
    except OSError as exc:
        os.close(descriptor)
        raise CandidateBuildError("output parent contains a symlink or non-directory") from exc
    except BaseException:
        os.close(descriptor)
        raise


def _new_staging_directory(parent_fd: int, output_name: str) -> tuple[str, int]:
    for _attempt in range(100):
        name = f".{output_name}.{secrets.token_hex(8)}"
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        return name, descriptor
    raise CandidateBuildError("could not reserve a fresh staging directory")


def _assert_named_directory_inode(parent_fd: int, name: str, descriptor: int) -> None:
    expected = os.fstat(descriptor)
    observed = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(observed.st_mode) or (observed.st_dev, observed.st_ino) != (expected.st_dev, expected.st_ino):
        raise CandidateBuildError("staging directory identity changed")


def _snapshot_regular_file(source: Path, target: Path, *, size: int, sha256: str) -> None:
    digest = hashlib.sha256()
    source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    target_fd = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        source_before = os.fstat(source_fd)
        with os.fdopen(target_fd, "wb", closefd=False) as output:
            while chunk := os.read(source_fd, 1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
            output.flush()
            os.fsync(output.fileno())
        source_after = os.fstat(source_fd)
    finally:
        os.close(target_fd)
        os.close(source_fd)
    if (
        (source_before.st_dev, source_before.st_ino, source_before.st_size, source_before.st_mtime_ns)
        != (source_after.st_dev, source_after.st_ino, source_after.st_size, source_after.st_mtime_ns)
        or source_after.st_size != size
        or digest.hexdigest() != sha256
    ):
        raise CandidateBuildError("source changed or differed while snapshotting")


def build(
    *,
    protocol_path: Path,
    pack_root: Path,
    downloads: Path,
    wheelhouse: Path,
    additive_root: Path,
    output: Path,
    mode: str,
    seed: int | None = None,
) -> dict[str, Any]:
    protocol_path = protocol_path.absolute()
    pack_root = pack_root.absolute()
    downloads = downloads.absolute()
    wheelhouse = wheelhouse.absolute()
    additive_root = additive_root.absolute()
    output = output.absolute()
    protocol = _load_protocol(protocol_path)
    python = Path(sys.executable)
    _validate_parent_environment(protocol)
    try:
        parent, parent_fd = _validated_output_parent(output)
    except (FileNotFoundError, OSError) as exc:
        raise CandidateBuildError("output parent is unavailable") from exc
    output_name = output.name
    output = parent / output_name
    try:
        try:
            os.stat(output_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise CandidateBuildError("output must be absent with an existing parent")
        if mode not in protocol["execution_boundary"]["modes"]:
            raise CandidateBuildError("unsupported build mode")
        wheel_identity = _wheelhouse_identity(wheelhouse)
        if wheel_identity != {key: protocol["wheelhouse"][key] for key in wheel_identity}:
            raise CandidateBuildError("wheelhouse identity changed")
        runtime = _runtime_probe(python, protocol)
        _validate_parent_module_origins(runtime)
        pack_asset, pack_identity = _verify_pack(pack_root, protocol)
        additive_identity = _validate_additive(additive_root, protocol)
        staging_name, staging_fd = _new_staging_directory(parent_fd, output_name)
        original_cwd_fd = os.open(".", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        os.fchdir(staging_fd)
        staging = Path(".")
    except BaseException:
        os.close(parent_fd)
        raise
    try:
        (staging / "input").mkdir(mode=0o700)
        snapshot_path = staging / "input" / "verified_golden_pack_snapshot.h5ad"
        _snapshot_regular_file(
            pack_asset,
            snapshot_path,
            size=protocol["pack"]["expression_size_bytes"],
            sha256=protocol["pack"]["expression_sha256"],
        )
        (staging / "gears-data").mkdir(mode=0o700)
        gene_payload = _regular_bytes(
            downloads / protocol["downloads"]["gene2go"]["filename"],
            size=protocol["downloads"]["gene2go"]["size_bytes"],
            sha256=protocol["downloads"]["gene2go"]["sha256"],
            label="gene2go",
        )
        essential_payload = _regular_bytes(
            downloads / protocol["downloads"]["essential_genes"]["filename"],
            size=protocol["downloads"]["essential_genes"]["size_bytes"],
            sha256=protocol["downloads"]["essential_genes"]["sha256"],
            label="essential genes",
        )
        go_payload = _regular_bytes(
            downloads / protocol["downloads"]["go_graph"]["filename"],
            size=protocol["downloads"]["go_graph"]["size_bytes"],
            sha256=protocol["downloads"]["go_graph"]["sha256"],
            label="GO graph",
        )
        gene2go = _validate_pickle(gene_payload, "gene2go")
        essential_values = _validate_pickle(essential_payload, "essential_genes")
        essential_genes = {str(value) for value in essential_values.tolist()}
        (staging / "gears-data" / "gene2go_all.pkl").write_bytes(gene_payload)
        (staging / "gears-data" / "essential_all_data_pert_genes.pkl").write_bytes(essential_payload)
        go_root = staging / "gears-data" / "go_essential_all"
        go_root.mkdir(mode=0o700)
        go_semantics = _validate_go_tar(go_payload, protocol["downloads"]["go_graph"], go_root)
        eligibility = set(gene2go).intersection(essential_genes)
        if not (
            go_semantics["sources"] == eligibility
            and go_semantics["targets"] == eligibility
            and go_semantics["self_edges"] == eligibility
        ):
            raise CandidateBuildError("GEARS graph gene universe differs across frozen assets")
        audit, derived = _reconstruct_train_input(
            str(snapshot_path),
            staging / "input" / "native_train_only.h5ad",
            protocol,
            gene2go,
            essential_genes,
        )
        _verify_pack(pack_root, protocol)
        snapshot_path.unlink()
        if mode != "prepare" or seed is not None:
            raise CandidateBuildError("model training is not implemented in this builder version")
        receipts: list[dict[str, Any]] = []
        native_input_record = _file_record(staging / "input" / "native_train_only.h5ad", single_link=True)
        record = {
            "schema_version": protocol["claim_ceiling"]["output_schema_version"],
            "record_role": protocol["claim_ceiling"]["output_record_role"],
            "mode": mode,
            "candidate_name": protocol["candidate"]["name"],
            "protocol_sha256": protocol["identity"]["payload_sha256"],
            "builder_sha256": protocol["identity"]["builder_sha256"],
            "pack": pack_identity,
            "additive_fallback": additive_identity,
            "wheelhouse": wheel_identity,
            "runtime": runtime,
            "contamination_audit": audit,
            "derived_input": {
                key: value for key, value in derived.items() if not key.startswith("internal_") and key != "graph_scope"
            },
            "derived_input_artifact": {
                "path": "input/native_train_only.h5ad",
                **native_input_record,
            },
            "graph_scope_audit": derived["graph_scope"],
            "graph_assets": {
                "eligibility_gene_count": len(eligibility),
                "eligibility_genes_sha256": _fingerprint(sorted(eligibility)),
                "go_data_rows": go_semantics["data_rows"],
            },
            "training_receipts": receipts,
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
        _publish(Path(staging_name), Path(output_name), parent_fd=parent_fd)
        _assert_named_directory_inode(parent_fd, output_name, staging_fd)
        os.fchdir(original_cwd_fd)
        return record
    except BaseException:
        os.fchdir(parent_fd)
        shutil.rmtree(staging_name, ignore_errors=True)
        os.fchdir(original_cwd_fd)
        raise
    finally:
        os.close(staging_fd)
        os.close(original_cwd_fd)
        os.close(parent_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=_PROTOCOL)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--additive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("prepare",), required=True)
    parser.add_argument("--seed", type=int)
    arguments = parser.parse_args(argv)
    build(
        protocol_path=arguments.protocol,
        pack_root=arguments.pack,
        downloads=arguments.downloads,
        wheelhouse=arguments.wheelhouse,
        additive_root=arguments.additive_root,
        output=arguments.output,
        mode=arguments.mode,
        seed=arguments.seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Prepare Golden-validation truth or run the frozen GEARS validation gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

_ROOT = Path(__file__).parents[1]
_BASE_PROTOCOL = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"
_VALIDATION_PROTOCOL = _ROOT / "data/golden/norman_2019/gears_train_only_validation_protocol.json"
_BUILDER = _ROOT / "scripts/build_golden_gears_train_only_candidate.py"
_TRAIN_RUNNER = _ROOT / "scripts/train_golden_gears_train_only_candidate.py"
_CONTROL_PREFIX = b"praxis-gears-predict-controls-v1\0"
_SEEDS = (11, 23, 37)
_TRUTH_FILES = {"metadata.json", "truth-delta.npy"}
_MODEL_FILES = {
    "candidate-record.json",
    "training.log",
    "model/config.pkl",
    "model/model.pt",
    "model/runtime-graph-manifest.json",
    "model/safe-config.json",
    "model/tensor-manifest.json",
}


class ValidationError(ValueError):
    """Fail-closed Golden validation error."""


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValidationError(f"required module is unavailable: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _builder():
    return _load_module("golden_gears_builder_for_validation", _BUILDER)


def _train_runner():
    return _load_module("golden_gears_train_runner_for_validation", _TRAIN_RUNNER)


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
        raise ValidationError("base GEARS protocol identity changed") from exc
    value = _strict_json(path, builder)
    if value.get("schema_version") != "praxis.golden-gears-train-only-validation-protocol.v1":
        raise ValidationError("unsupported validation protocol")
    identity = value.get("identity", {})
    copy = json.loads(builder._canonical_bytes(value))
    copy["identity"]["payload_sha256"] = None
    if not (
        identity.get("payload_hash_algorithm")
        == "sha256(canonical_json(protocol_with_identity.payload_sha256_set_to_null))"
        and identity.get("payload_sha256") == builder._fingerprint(copy)
        and identity.get("base_protocol_path") == "data/golden/norman_2019/gears_train_only_protocol.json"
        and identity.get("base_protocol_payload_sha256") == base["identity"]["payload_sha256"]
        and identity.get("evaluator_path") == "scripts/evaluate_golden_gears_train_only_validation.py"
        and identity.get("evaluator_sha256") == builder._sha256(Path(__file__))
    ):
        raise ValidationError("validation protocol identity changed")
    return value, base, builder


def _require_frozen(protocol: dict[str, Any]) -> None:
    if not (
        protocol.get("implementation_status") == "FROZEN_EXECUTABLE"
        and protocol.get("truth_bundle", {}).get("status") == "FROZEN"
        and protocol.get("candidate_set", {}).get("status") == "FROZEN"
    ):
        raise ValidationError("validation inputs are not frozen; evaluation is not executable")


def _safe_relative(value: str, label: str) -> Path:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValidationError(f"unsafe {label} path")
    return Path(*path.parts)


def _regular_inventory(root: Path) -> set[str]:
    if root.is_symlink() or not root.is_dir():
        raise ValidationError("artifact root must be a regular directory")
    files: set[str] = set()
    for path in root.rglob("*"):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValidationError("artifact inventory contains an unsafe entry")
        if stat.S_ISREG(info.st_mode):
            files.add(path.relative_to(root).as_posix())
    return files


def _array_sha256(value: np.ndarray, dtype: str) -> str:
    return hashlib.sha256(np.asarray(value, dtype=dtype).tobytes(order="C")).hexdigest()


def _control_entropy(seed: int, targets: tuple[str, ...], builder) -> tuple[int, str]:
    if seed not in _SEEDS or tuple(sorted(targets)) != targets or len(targets) not in {1, 2}:
        raise ValidationError("invalid control-sampling query")
    material = _CONTROL_PREFIX + str(seed).encode("ascii") + b"\0" + builder._canonical_bytes(list(targets))
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:16], "big", signed=False), digest.hex()


def _control_indices(seed: int, targets: tuple[str, ...], builder, *, controls: int = 2059) -> tuple[np.ndarray, str]:
    entropy, digest = _control_entropy(seed, targets, builder)
    rng = np.random.Generator(np.random.PCG64(entropy))
    indices = rng.integers(0, controls, size=300, endpoint=False, dtype=np.int64)
    return indices, digest


def _write_new_directory(output: Path, builder, writer: Callable[[Path], Any]) -> Any:
    output = output.absolute()
    parent, parent_fd = builder._validated_output_parent(output)
    name = ""
    directory_fd = -1
    try:
        try:
            os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValidationError("output must be write-new")
        name, directory_fd = builder._new_staging_directory(parent_fd, output.name)
        staging = parent / name
        result = writer(staging)
        builder._assert_named_directory_inode(parent_fd, name, directory_fd)
        builder._publish(Path(name), Path(output.name), parent_fd=parent_fd)
        builder._assert_named_directory_inode(parent_fd, output.name, directory_fd)
        return result
    except BaseException:
        if name:
            shutil.rmtree(parent / name, ignore_errors=True)
        raise
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        os.close(parent_fd)


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


def _validation_truth(pack_asset: Path, base: dict[str, Any], builder) -> tuple[dict[str, Any], np.ndarray]:
    import anndata
    from scipy import sparse

    before = pack_asset.stat()
    source = anndata.read_h5ad(pack_asset, backed="r")
    try:
        if list(source.shape) != base["pack"]["shape"]:
            raise ValidationError("Golden expression shape changed")
        obs = source.obs
        feature_ids = list(map(str, source.var_names))
        symbols = list(map(str, source.var[base["pack"]["feature_symbol_field"]]))
        if not (
            len(symbols) == len(set(symbols))
            and builder._fingerprint(feature_ids) == base["pack"]["feature_ids_sha256"]
            and builder._fingerprint(symbols) == base["pack"]["feature_symbols_sha256"]
            and builder._fingerprint(list(map(str, obs.index))) == base["pack"]["observation_ids_sha256"]
            and builder._fingerprint(list(map(str, obs[base["pack"]["split_field"]])))
            == base["pack"]["golden_split_by_observation_sha256"]
            and builder._fingerprint(list(map(str, obs[base["pack"]["condition_field"]])))
            == base["pack"]["condition_id_by_observation_sha256"]
        ):
            raise ValidationError("Golden ordered identity changed")
        audit, condition_targets = builder._split_audit(obs, base)
        expected = base["contamination_contract"]["expected"]
        if audit["status"] != "passed":
            raise ValidationError("Golden split audit failed")
        split = np.asarray(obs[base["pack"]["split_field"]].astype(str))
        validation_positions = np.flatnonzero(split == "validation")
        if len(validation_positions) != expected["rows"]["validation"]:
            raise ValidationError("Golden validation row count changed")
        labels = np.asarray(obs.iloc[validation_positions][base["pack"]["condition_field"]].astype(str))
        control_id = base["pack"]["control_condition_ids"]["validation"]
        condition_ids = sorted(set(labels).difference({control_id}))
        if not (
            len(condition_ids) == expected["noncontrol_conditions"]["validation"]
            and builder._fingerprint(condition_ids) == expected["condition_set_sha256"]["validation"]
        ):
            raise ValidationError("Golden validation condition identity changed")
        all_labels = [control_id, *condition_ids]
        sums = {condition: np.zeros(len(feature_ids), dtype=np.float64) for condition in all_labels}
        counts = dict.fromkeys(all_labels, 0)
        for start in range(0, len(validation_positions), 256):
            positions = validation_positions[start : start + 256]
            block_labels = labels[start : start + 256]
            block = source.X[positions]
            if sparse.issparse(block):
                block = block.toarray()
            block = np.asarray(block, dtype=np.float64)
            for condition in sorted(set(block_labels)):
                selected = block[block_labels == condition]
                sums[condition] += selected.sum(axis=0, dtype=np.float64)
                counts[condition] += len(selected)
        if counts[control_id] != expected["controls"]["validation"] or any(not counts[item] for item in condition_ids):
            raise ValidationError("Golden validation expression coverage changed")
        control_mean = sums[control_id] / counts[control_id]
        truth = np.stack([sums[item] / counts[item] - control_mean for item in condition_ids]).astype("<f8")
        if truth.shape != (30, 5045) or not np.isfinite(truth).all():
            raise ValidationError("Golden validation truth is invalid")
        symbol_to_id = dict(zip(symbols, feature_ids, strict=True))
        records = []
        for row, condition in enumerate(condition_ids):
            targets = condition_targets[condition]
            if not set(targets).issubset(symbol_to_id):
                raise ValidationError("Golden validation target is absent from ordered features")
            records.append(
                {
                    "condition_id": condition,
                    "targets": list(targets),
                    "target_feature_ids": [symbol_to_id[target] for target in targets],
                    "scope": "single" if len(targets) == 1 else "combination",
                    "truth_row": row,
                    "observations": counts[condition],
                }
            )
        tuples = sorted({tuple(record["targets"]) for record in records})
        singles = sum(record["scope"] == "single" for record in records)
        combinations = sum(record["scope"] == "combination" for record in records)
        if not (
            len(tuples) == expected["canonical_symbol_target_tuple_set"]["validation"]["count"]
            and builder._fingerprint([list(item) for item in tuples])
            == expected["canonical_symbol_target_tuple_set"]["validation"]["sha256"]
            and singles == expected["single_conditions"]["validation"]
            and combinations == expected["combination_conditions"]["validation"]
        ):
            raise ValidationError("Golden validation canonical scope changed")
        validation_ids = list(map(str, obs.index[validation_positions]))
        metadata = {
            "schema_version": "praxis.golden-gears-validation-truth-bundle.v1",
            "record_role": "validation_only_truth_not_test_and_not_model_evidence",
            "base_protocol_payload_sha256": base["identity"]["payload_sha256"],
            "evaluator_sha256": builder._sha256(Path(__file__)),
            "pack": {
                "pack_id": base["pack"]["pack_id"],
                "pack_version": base["pack"]["pack_version"],
                "pack_fingerprint": base["pack"]["pack_fingerprint"],
                "expression_sha256": base["pack"]["expression_sha256"],
            },
            "decoded_expression_partitions": ["validation"],
            "test_expression_decoded": False,
            "test_outcomes_used": False,
            "validation": {
                "rows": len(validation_positions),
                "controls": counts[control_id],
                "control_condition_id": control_id,
                "observation_ids_source_order_sha256": builder._fingerprint(validation_ids),
                "condition_count": len(records),
                "single_condition_count": singles,
                "combination_condition_count": combinations,
                "condition_ids_sha256": builder._fingerprint(condition_ids),
                "canonical_target_tuples": len(tuples),
                "canonical_target_tuples_sha256": builder._fingerprint([list(item) for item in tuples]),
            },
            "features": {
                "count": len(feature_ids),
                "ordered_feature_ids_sha256": builder._fingerprint(feature_ids),
                "ordered_feature_symbols_sha256": builder._fingerprint(symbols),
            },
            "conditions": records,
            "truth_delta": {
                "filename": "truth-delta.npy",
                "shape": list(truth.shape),
                "dtype": "float64_little_endian",
                "definition": "validation_condition_mean_X_minus_matched_validation_control_mean_X",
                "reduction_dtype": "float64",
            },
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
        }
    finally:
        source.file.close()
    after = pack_asset.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise ValidationError("Golden Pack changed while preparing validation truth")
    return metadata, truth


def prepare_validation(*, protocol_path: Path, pack_root: Path, output: Path) -> dict[str, Any]:
    protocol, base, builder = _load_protocol(protocol_path)
    if protocol.get("truth_bundle", {}).get("status") != "PENDING_FREEZE":
        raise ValidationError("truth preparation requires a PENDING_FREEZE protocol")
    try:
        pack_asset, _identity = builder._verify_pack(pack_root.absolute(), base)
    except Exception as exc:
        raise ValidationError("Golden Pack identity changed") from exc
    metadata, truth = _validation_truth(pack_asset, base, builder)

    def write(staging: Path) -> dict[str, Any]:
        np.save(staging / "truth-delta.npy", truth, allow_pickle=False)
        array_record = builder._file_record(staging / "truth-delta.npy", single_link=True)
        metadata["truth_delta"].update(array_record)
        (staging / "metadata.json").write_bytes(builder._canonical_bytes(metadata) + b"\n")
        if _regular_inventory(staging) != _TRUTH_FILES:
            raise ValidationError("truth bundle inventory changed")
        return metadata

    return _write_new_directory(output, builder, write)


def _verify_truth_bundle(root: Path, protocol: dict[str, Any], base: dict[str, Any], builder):
    expected = protocol["truth_bundle"]
    if _regular_inventory(root) != _TRUTH_FILES:
        raise ValidationError("truth bundle inventory changed")
    for name in sorted(_TRUTH_FILES):
        if builder._file_record(root / name, single_link=True) != expected["files"][name]:
            raise ValidationError(f"truth bundle identity changed: {name}")
    metadata = _strict_json(root / "metadata.json", builder)
    validation = metadata.get("validation", {})
    features = metadata.get("features", {})
    records = metadata.get("conditions")
    truth_record = metadata.get("truth_delta", {})
    expected_split = base["contamination_contract"]["expected"]
    if not (
        metadata.get("schema_version") == "praxis.golden-gears-validation-truth-bundle.v1"
        and metadata.get("base_protocol_payload_sha256") == base["identity"]["payload_sha256"]
        and metadata.get("evaluator_sha256") == protocol["identity"]["evaluator_sha256"]
        and metadata.get("decoded_expression_partitions") == ["validation"]
        and metadata.get("test_expression_decoded") is False
        and metadata.get("test_outcomes_used") is False
        and validation.get("rows") == expected_split["rows"]["validation"]
        and validation.get("controls") == expected_split["controls"]["validation"]
        and validation.get("control_condition_id") == base["pack"]["control_condition_ids"]["validation"]
        and validation.get("condition_count") == expected_split["noncontrol_conditions"]["validation"]
        and validation.get("single_condition_count") == expected_split["single_conditions"]["validation"]
        and validation.get("combination_condition_count") == expected_split["combination_conditions"]["validation"]
        and validation.get("condition_ids_sha256") == expected_split["condition_set_sha256"]["validation"]
        and validation.get("canonical_target_tuples")
        == expected_split["canonical_symbol_target_tuple_set"]["validation"]["count"]
        and validation.get("canonical_target_tuples_sha256")
        == expected_split["canonical_symbol_target_tuple_set"]["validation"]["sha256"]
        and features
        == {
            "count": base["pack"]["shape"][1],
            "ordered_feature_ids_sha256": base["pack"]["feature_ids_sha256"],
            "ordered_feature_symbols_sha256": base["pack"]["feature_symbols_sha256"],
        }
        and isinstance(records, list)
        and len(records) == 30
        and truth_record.get("filename") == "truth-delta.npy"
        and truth_record.get("shape") == [30, 5045]
        and truth_record.get("dtype") == "float64_little_endian"
        and {key: truth_record.get(key) for key in ("size_bytes", "sha256")} == expected["files"]["truth-delta.npy"]
        and metadata.get("benchmark_status") == "NOT_RUN"
        and metadata.get("benchmark_passed") is None
        and metadata.get("scientifically_validated") is False
        and metadata.get("promotion_eligible") is False
        and metadata.get("production_promoted") is False
    ):
        raise ValidationError("truth bundle metadata changed")
    condition_ids = []
    target_tuples = set()
    for row, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValidationError("truth condition record is invalid")
        condition = record.get("condition_id")
        try:
            targets = tuple(record.get("targets", ()))
            canonical = builder._canonical_targets(condition)
        except Exception as exc:
            raise ValidationError("truth condition target grammar changed") from exc
        if not (
            targets == canonical
            and record.get("scope") == ("single" if len(targets) == 1 else "combination")
            and record.get("truth_row") == row
            and isinstance(record.get("target_feature_ids"), list)
            and len(record["target_feature_ids"]) == len(targets)
            and isinstance(record.get("observations"), int)
            and record["observations"] > 0
        ):
            raise ValidationError("truth condition record changed")
        condition_ids.append(condition)
        target_tuples.add(targets)
    if not (
        condition_ids == sorted(condition_ids)
        and builder._fingerprint(condition_ids) == validation["condition_ids_sha256"]
        and builder._fingerprint([list(item) for item in sorted(target_tuples)])
        == validation["canonical_target_tuples_sha256"]
    ):
        raise ValidationError("truth condition ordering changed")
    try:
        truth = np.load(root / "truth-delta.npy", allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise ValidationError("truth array is invalid") from exc
    if truth.dtype.str != "<f8" or truth.shape != (30, 5045) or not np.isfinite(truth).all():
        raise ValidationError("truth array contract changed")
    return metadata, truth


def _verify_prepare_root(root: Path, base: dict[str, Any], builder):
    runner = _train_runner()
    if builder._sha256(_TRAIN_RUNNER) != base["identity"]["train_runner_sha256"]:
        raise ValidationError("base train runner identity changed")
    try:
        record, record_sha256 = runner._verify_prepare_root(root.absolute(), builder, base)
        split = runner._verify_h5ad(root.absolute() / "input/native_train_only.h5ad", base, builder)
        gene_payload = builder._regular_bytes(
            root.absolute() / "gears-data/gene2go_all.pkl",
            size=base["downloads"]["gene2go"]["size_bytes"],
            sha256=base["downloads"]["gene2go"]["sha256"],
            label="gene2go",
        )
        essential_payload = builder._regular_bytes(
            root.absolute() / "gears-data/essential_all_data_pert_genes.pkl",
            size=base["downloads"]["essential_genes"]["size_bytes"],
            sha256=base["downloads"]["essential_genes"]["sha256"],
            label="essential genes",
        )
        gene2go = builder._validate_pickle(gene_payload, "gene2go")
        essential = set(map(str, builder._validate_pickle(essential_payload, "essential_genes").tolist()))
    except Exception as exc:
        raise ValidationError("prepared train-only artifact identity changed") from exc
    eligible = set(gene2go).intersection(essential)
    expected = base["candidate"]["fallback"]["eligibility_gene_set"]
    if len(eligible) != expected["count"] or builder._fingerprint(sorted(eligible)) != expected["sha256"]:
        raise ValidationError("GEARS eligibility vocabulary changed")
    return record, record_sha256, split, eligible


def _validate_candidate_record(
    record: dict[str, Any], expected: dict[str, Any], base: dict[str, Any], prepare_sha256: str
) -> None:
    seed = expected["seed"]
    execution = record.get("execution", {})
    if not (
        record.get("schema_version") == "praxis.golden-gears-train-only-full-seed-candidate.v1"
        and record.get("record_role") == "manifest_bound_full_training_candidate_not_scientific_evidence"
        and record.get("candidate_name") == base["candidate"]["name"]
        and record.get("mode") == "full_train"
        and record.get("protocol_sha256") == base["identity"]["payload_sha256"]
        and record.get("prepare_record_sha256") == prepare_sha256
        and record.get("prepare_input")
        == {
            "path": "input/native_train_only.h5ad",
            **base["execution_boundary"]["prepared_artifact_attestation"]["native_train_only_h5ad"],
        }
        and execution.get("seed") == seed
        and execution.get("epochs") == base["training"]["model"]["max_epochs"]
        and execution.get("batch_size") == base["training"]["model"]["batch_size"]
        and execution.get("golden_validation_expression_or_outcomes_read") is False
        and execution.get("golden_test_expression_or_outcomes_read") is False
        and execution.get("golden_validation_or_test_paths_provided_to_child") is False
        and execution.get("test_loader_present") is False
        and record.get("benchmark_status") == "NOT_RUN"
        and record.get("benchmark_passed") is None
        and record.get("scientifically_validated") is False
        and record.get("promotion_eligible") is False
        and record.get("production_promoted") is False
        and record.get("registry_or_default_route_changed") is False
    ):
        raise ValidationError(f"seed {seed} candidate record changed")


def _verify_candidate_runtime_manifests(
    directory: Path, expected: dict[str, Any], protocol: dict[str, Any], base: dict[str, Any], builder
) -> None:
    safe_path = directory / "model/safe-config.json"
    graph_path = directory / "model/runtime-graph-manifest.json"
    if not (
        builder._file_record(safe_path, single_link=True) == expected["safe_config"]
        and builder._file_record(graph_path, single_link=True) == expected["runtime_graph_manifest"]
    ):
        raise ValidationError(f"seed {expected['seed']} safe runtime manifest identity changed")
    safe = _strict_json(safe_path, builder)
    graph = _strict_json(graph_path, builder)
    if safe != {"schema_version": "praxis.golden-gears-safe-config.v1", "model": base["training"]["model"]}:
        raise ValidationError(f"seed {expected['seed']} safe model configuration changed")
    expected_graph = protocol["inference"]["candidate_runtime_graph_manifest"]
    normalized = json.loads(builder._canonical_bytes(graph))
    normalized["seed"] = None
    if not (graph.get("seed") == expected["seed"] and normalized == expected_graph):
        raise ValidationError(f"seed {expected['seed']} runtime graph or vocabulary changed")


def _verify_candidates(
    root: Path, protocol: dict[str, Any], base: dict[str, Any], builder, prepare_sha256: str
) -> list[dict[str, Any]]:
    if root.is_symlink() or not root.is_dir():
        raise ValidationError("candidate set root must be a regular directory")
    records = protocol["candidate_set"].get("seeds")
    if not isinstance(records, list) or [item.get("seed") for item in records] != list(_SEEDS):
        raise ValidationError("candidate seed order changed")
    collection_expected = protocol["candidate_set"].get("collection_record")
    if not isinstance(collection_expected, dict):
        raise ValidationError("candidate collection receipt is absent")
    expected_inventory = {"collection-record.json"}
    for item in records:
        directory = _safe_relative(item["directory"], "candidate").as_posix()
        expected_inventory.update(f"{directory}/{relative}" for relative in _MODEL_FILES)
    if _regular_inventory(root) != expected_inventory:
        raise ValidationError("candidate collection inventory changed")
    collection_path = root / "collection-record.json"
    if builder._file_record(collection_path, single_link=True) != collection_expected:
        raise ValidationError("candidate collection receipt identity changed")
    collection = _strict_json(collection_path, builder)
    if not (
        collection.get("schema_version") == "praxis.golden-gears-train-only-full-collection.v1"
        and collection.get("record_role") == "manifest_bound_full_training_collection_not_scientific_evidence"
        and collection.get("status") == "completed"
        and collection.get("candidate_name") == base["candidate"]["name"]
        and collection.get("protocol_sha256") == base["identity"]["payload_sha256"]
        and collection.get("prepare_record_sha256") == prepare_sha256
        and collection.get("execution", {}).get("seeds") == list(_SEEDS)
        and collection.get("execution", {}).get("epochs_per_seed") == base["training"]["model"]["max_epochs"]
        and collection.get("execution", {}).get("batch_size") == base["training"]["model"]["batch_size"]
        and collection.get("execution", {}).get("golden_validation_expression_or_outcomes_read") is False
        and collection.get("execution", {}).get("golden_test_expression_or_outcomes_read") is False
        and collection.get("benchmark_status") == "NOT_RUN"
        and collection.get("benchmark_passed") is None
        and collection.get("scientifically_validated") is False
        and collection.get("promotion_eligible") is False
        and collection.get("production_promoted") is False
        and collection.get("registry_or_default_route_changed") is False
    ):
        raise ValidationError("candidate collection semantics changed")
    collection_seeds = collection.get("seeds")
    if not isinstance(collection_seeds, list) or [item.get("seed") for item in collection_seeds] != list(_SEEDS):
        raise ValidationError("candidate collection seed order changed")
    runner = _train_runner()
    verified = []
    for expected, collection_seed in zip(records, collection_seeds, strict=True):
        seed = expected["seed"]
        directory = root / _safe_relative(expected["directory"], "candidate")
        record_path = directory / "candidate-record.json"
        manifest_path = directory / "model/tensor-manifest.json"
        model_path = directory / "model/model.pt"
        if builder._file_record(record_path, single_link=True) != expected["candidate_record"]:
            raise ValidationError(f"seed {seed} candidate receipt identity changed")
        if builder._file_record(model_path, single_link=True) != expected["model_pt"]:
            raise ValidationError(f"seed {seed} checkpoint identity changed")
        if builder._file_record(manifest_path, single_link=True) != expected["tensor_manifest"]:
            raise ValidationError(f"seed {seed} tensor manifest identity changed")
        if not (
            collection_seed.get("candidate_record", {}).get("path") == f"seed-{seed}/candidate-record.json"
            and {key: collection_seed["candidate_record"].get(key) for key in ("size_bytes", "sha256")}
            == expected["candidate_record"]
            and collection_seed.get("model_pt", {}).get("path") == f"seed-{seed}/model/model.pt"
            and {key: collection_seed["model_pt"].get(key) for key in ("size_bytes", "sha256")} == expected["model_pt"]
            and collection_seed.get("tensor_manifest", {}).get("path") == f"seed-{seed}/model/tensor-manifest.json"
            and {key: collection_seed["tensor_manifest"].get(key) for key in ("size_bytes", "sha256")}
            == expected["tensor_manifest"]
            and collection_seed.get("safe_config", {}).get("path") == f"seed-{seed}/model/safe-config.json"
            and {key: collection_seed["safe_config"].get(key) for key in ("size_bytes", "sha256")}
            == expected["safe_config"]
            and collection_seed.get("runtime_graph_manifest", {}).get("path")
            == f"seed-{seed}/model/runtime-graph-manifest.json"
            and {key: collection_seed["runtime_graph_manifest"].get(key) for key in ("size_bytes", "sha256")}
            == expected["runtime_graph_manifest"]
        ):
            raise ValidationError(f"seed {seed} collection binding changed")
        record = _strict_json(record_path, builder)
        _validate_candidate_record(record, expected, base, prepare_sha256)
        _verify_candidate_runtime_manifests(directory, expected, protocol, base, builder)
        manifest = _strict_json(manifest_path, builder)
        try:
            runner._validate_tensor_manifest(manifest)
        except Exception as exc:
            raise ValidationError(f"seed {seed} tensor manifest is invalid") from exc
        artifacts = record.get("artifacts", {})
        if not (
            {key: artifacts.get("model.pt", {}).get(key) for key in ("size_bytes", "sha256")} == expected["model_pt"]
            and {key: artifacts.get("tensor-manifest.json", {}).get(key) for key in ("size_bytes", "sha256")}
            == expected["tensor_manifest"]
            and artifacts.get("safe-config.json") == expected["safe_config"]
            and artifacts.get("runtime-graph-manifest.json") == expected["runtime_graph_manifest"]
            and artifacts.get("model.pt", {}).get("weights_only_verified") is True
        ):
            raise ValidationError(f"seed {seed} model artifact receipt changed")
        verified.append({"seed": seed, "root": directory, "model_pt": expected["model_pt"]})
    return verified


_CHILD = r"""
import hashlib,json,random
from pathlib import Path
root=Path.cwd(); job=json.loads((root/'job.json').read_text())
import dcor
import numpy as np,pandas as pd,torch
pd.Series.nonzero=lambda self:self.to_numpy().nonzero()
from gears import GEARS,PertData
from gears.utils import create_cell_graph_for_prediction
from torch_geometric.loader import DataLoader
import anndata
def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def fingerprint(value): return hashlib.sha256(canonical(value)).hexdigest()
def array_record(tensor):
 a=tensor.detach().cpu().contiguous().numpy(); dtype='>i8' if a.dtype.kind in 'iu' else '>f4'
 return {'shape':list(a.shape),'dtype':dtype,'sha256':hashlib.sha256(np.asarray(a,dtype=dtype).tobytes()).hexdigest()}
def native_record(tensor):
 value=tensor.detach().cpu().contiguous()
 return {'shape':list(value.shape),'dtype':str(value.dtype),'numel':value.numel(),
  'sha256':hashlib.sha256(value.numpy().tobytes()).hexdigest(),'finite':True}
def reset(seed):
 random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
reset(0); torch.use_deterministic_algorithms(True); torch.set_num_threads(1); torch.set_num_interop_threads(1)
adata=anndata.read_h5ad(root/'input/native_train_only.h5ad')
pd_=PertData(str(root/'work'))
reset(0); pd_.new_data_process('norman_golden_train_only',adata=adata,skip_calc_de=False)
pd_.split='no_test'; pd_.seed=0; pd_.train_gene_set_size=None; pd_.subgroup=None
pd_.set2conditions=job['split']; pd_.get_dataloader(batch_size=job['batch_size'])
if set(pd_.dataloader) != {'train_loader','val_loader'}: raise RuntimeError('held-out loader present')
reset(0); g=GEARS(pd_,device='cpu',weight_bias_track=False); m=job['model']
g.model_initialize(hidden_size=m['hidden_size'],num_go_gnn_layers=m['num_go_gnn_layers'],
 num_gene_gnn_layers=m['num_gene_gnn_layers'],decoder_hidden_size=m['decoder_hidden_size'],
 num_similar_genes_go_graph=m['num_similar_genes_go_graph'],
 num_similar_genes_co_express_graph=m['num_similar_genes_co_express_graph'],
 coexpress_threshold=m['coexpress_threshold'],uncertainty=m['uncertainty'],
 uncertainty_reg=m['uncertainty_reg'],direction_lambda=m['direction_lambda'],no_perturb=m['no_perturb'])
graphs={key:array_record(g.config[key]) for key in ('G_coexpress','G_coexpress_weight','G_go','G_go_weight')}
genes=list(map(str,g.gene_list)); perts=list(map(str,g.pert_list))
raw_graph_manifest={'schema_version':'praxis.gears-runtime-graph-manifest.v1','seed':None,
 'vocabularies':{
  'gene':{'count':len(genes),'canonical_json_sha256':fingerprint(genes)},
  'perturbation':{'count':len(perts),'canonical_json_sha256':fingerprint(perts)}},
 'graphs':{
  'G_go':{'node_vocabulary':'perturbation','edge_index':native_record(g.config['G_go']),
          'edge_weight':native_record(g.config['G_go_weight'])},
  'G_coexpress':{'node_vocabulary':'gene','edge_index':native_record(g.config['G_coexpress']),
                 'edge_weight':native_record(g.config['G_coexpress_weight'])}}}
ctrl=pd_.adata[pd_.adata.obs.condition.astype(str)=='ctrl']
ctrl_ids=list(map(str,ctrl.obs_names)); ctrl_sum=np.zeros(pd_.adata.n_vars,dtype=np.float64)
for start in range(0,len(ctrl),256):
 block=ctrl.X[start:start+256]
 if hasattr(block,'toarray'): block=block.toarray()
 ctrl_sum += np.asarray(block,dtype=np.float64).sum(axis=0,dtype=np.float64)
ctrl_mean=ctrl_sum/len(ctrl)
vocab={'ordered_feature_symbols_sha256':fingerprint(list(map(str,pd_.gene_names))),
 'perturbation_vocabulary_sha256':fingerprint(list(map(str,pd_.pert_names))),
 'train_control_observation_ids_source_order_sha256':fingerprint(ctrl_ids),
 'train_control_mean_sha256':hashlib.sha256(np.asarray(ctrl_mean,dtype='>f8').tobytes()).hexdigest(),
 'train_control_count':len(ctrl)}
if (graphs != job['expected_graphs'] or vocab != job['expected_vocab']
 or raw_graph_manifest != job['expected_raw_graph_manifest']):
 raise RuntimeError('graph or vocabulary identity changed')
queries=[tuple(value) for value in job['queries']]; predictions=[]; samples=[]
for candidate in job['candidates']:
 seed=candidate['seed']; state=torch.load(root/candidate['model_pt'],map_location='cpu',weights_only=True)
 if not isinstance(state,dict) or not state: raise RuntimeError('empty or unsafe state dict')
 g.model.load_state_dict(state,strict=True); g.model.eval(); seed_predictions=[]
 with torch.inference_mode():
  for targets in queries:
   material=b'praxis-gears-predict-controls-v1\0'+str(seed).encode('ascii')+b'\0'+canonical(list(targets))
   digest=hashlib.sha256(material).digest(); entropy=int.from_bytes(digest[:16],'big',signed=False)
   rng=np.random.Generator(np.random.PCG64(entropy))
   indices=rng.integers(0,len(ctrl),size=300,endpoint=False,dtype=np.int64)
   block=ctrl[indices,:].X
   if hasattr(block,'toarray'): block=block.toarray()
   pert_idx=[int(np.where(name==pd_.pert_names)[0][0]) for name in targets]
   graphs_for_query=[create_cell_graph_for_prediction(row,pert_idx,list(targets)) for row in np.asarray(block)]
   batch=next(iter(DataLoader(graphs_for_query,batch_size=300,shuffle=False))).to('cpu')
   output=g.model(batch)
   if isinstance(output,tuple): output=output[0]
   value=output.detach().to(dtype=torch.float64).mean(dim=0).cpu().numpy()-ctrl_mean
   if value.shape != (5045,) or not np.isfinite(value).all(): raise RuntimeError('non-finite prediction')
   seed_predictions.append(value)
   samples.append({'seed':seed,'targets':list(targets),'digest_sha256':digest.hex(),
    'indices_sha256':hashlib.sha256(np.asarray(indices,dtype='>u8').tobytes()).hexdigest()})
 predictions.append(seed_predictions)
value=np.asarray(predictions,dtype='<f8'); np.save(root/'predictions.npy',value,allow_pickle=False)
receipt={'status':'completed','seeds':[item['seed'] for item in job['candidates']],
 'query_count':len(queries),'prediction_shape':list(value.shape),'prediction_dtype':'float64_little_endian',
 'prediction_sha256':hashlib.sha256((root/'predictions.npy').read_bytes()).hexdigest(),
 'graphs':graphs,'raw_graph_manifest':raw_graph_manifest,
 'vocabulary':vocab,'control_samples':samples,'test_loader_present':False,
 'model_config_pickle_read':False,'weights_only':True,'strict_state_load':True,
 'model_eval':True,'torch_inference_mode':True}
(root/'child-receipt.json').write_text(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n')
"""


def _run_inference(
    *,
    prepare_root: Path,
    candidates: list[dict[str, Any]],
    queries: list[tuple[str, ...]],
    split: dict[str, list[str]],
    protocol: dict[str, Any],
    base: dict[str, Any],
    builder,
    output_parent: Path,
) -> tuple[np.ndarray, dict[str, Any], dict[str, str]]:
    train_runner = _train_runner()
    try:
        runtime = train_runner._verify_runtime(builder, base)
    except Exception as exc:
        raise ValidationError("frozen GEARS runtime identity changed") from exc
    parent, parent_fd = builder._validated_output_parent((output_parent / "validation-receipt.json").absolute())
    name = ""
    directory_fd = -1
    try:
        name, directory_fd = builder._new_staging_directory(parent_fd, "gears-validation-work")
        staging = parent / name
        (staging / "input").mkdir(mode=0o700)
        (staging / "work/go_essential_all").mkdir(parents=True, mode=0o700)
        copies = {
            prepare_root / "input/native_train_only.h5ad": (
                staging / "input/native_train_only.h5ad",
                base["execution_boundary"]["prepared_artifact_attestation"]["native_train_only_h5ad"],
            ),
            prepare_root / "gears-data/gene2go_all.pkl": (
                staging / "work/gene2go_all.pkl",
                base["downloads"]["gene2go"],
            ),
            prepare_root / "gears-data/essential_all_data_pert_genes.pkl": (
                staging / "work/essential_all_data_pert_genes.pkl",
                base["downloads"]["essential_genes"],
            ),
            prepare_root / "gears-data/go_essential_all/go_essential_all.csv": (
                staging / "work/go_essential_all/go_essential_all.csv",
                base["downloads"]["go_graph"]["csv"],
            ),
        }
        for source, (target, record) in copies.items():
            builder._snapshot_regular_file(source, target, size=record["size_bytes"], sha256=record["sha256"])
        child_candidates = []
        for candidate in candidates:
            model_dir = staging / f"models/seed-{candidate['seed']}"
            model_dir.mkdir(parents=True, mode=0o700)
            target = model_dir / "model.pt"
            builder._snapshot_regular_file(
                candidate["root"] / "model/model.pt",
                target,
                size=candidate["model_pt"]["size_bytes"],
                sha256=candidate["model_pt"]["sha256"],
            )
            child_candidates.append({"seed": candidate["seed"], "model_pt": target.relative_to(staging).as_posix()})
        inference = protocol["inference"]
        job = {
            "split": split,
            "batch_size": base["training"]["model"]["batch_size"],
            "model": base["training"]["model"],
            "queries": [list(item) for item in queries],
            "candidates": child_candidates,
            "expected_graphs": inference["reconstructed_graphs"],
            "expected_raw_graph_manifest": inference["candidate_runtime_graph_manifest"],
            "expected_vocab": inference["vocabulary"],
        }
        (staging / "job.json").write_bytes(builder._canonical_bytes(job))
        if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
            raise ValidationError("network-denying sandbox is unavailable")
        result = subprocess.run(
            ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)", sys.executable, "-c", _CHILD],
            cwd=staging,
            env=builder._child_env(staging=staging),
            capture_output=True,
            check=False,
        )
        logs = {
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        }
        if result.returncode:
            raise ValidationError("GEARS validation inference child failed")
        receipt = _strict_json(staging / "child-receipt.json", builder)
        try:
            prediction = np.load(staging / "predictions.npy", allow_pickle=False)
        except (OSError, ValueError) as exc:
            raise ValidationError("GEARS validation prediction is invalid") from exc
        expected_shape = (3, len(queries), base["pack"]["shape"][1])
        if not (
            prediction.dtype.str == "<f8"
            and prediction.shape == expected_shape
            and np.isfinite(prediction).all()
            and receipt.get("status") == "completed"
            and receipt.get("seeds") == list(_SEEDS)
            and receipt.get("query_count") == len(queries)
            and receipt.get("prediction_shape") == list(expected_shape)
            and receipt.get("prediction_dtype") == "float64_little_endian"
            and receipt.get("prediction_sha256") == builder._sha256(staging / "predictions.npy")
            and receipt.get("graphs") == inference["reconstructed_graphs"]
            and receipt.get("raw_graph_manifest") == inference["candidate_runtime_graph_manifest"]
            and receipt.get("vocabulary") == inference["vocabulary"]
            and receipt.get("test_loader_present") is False
            and receipt.get("model_config_pickle_read") is False
            and receipt.get("weights_only") is True
            and receipt.get("strict_state_load") is True
            and receipt.get("model_eval") is True
            and receipt.get("torch_inference_mode") is True
            and len(receipt.get("control_samples", ())) == len(_SEEDS) * len(queries)
        ):
            raise ValidationError("GEARS validation child receipt changed")
        expected_samples = []
        for seed in _SEEDS:
            for targets in queries:
                indices, digest = _control_indices(seed, targets, builder)
                expected_samples.append(
                    {
                        "seed": seed,
                        "targets": list(targets),
                        "digest_sha256": digest,
                        "indices_sha256": _array_sha256(indices, ">u8"),
                    }
                )
        if receipt["control_samples"] != expected_samples:
            raise ValidationError("control sampling changed")
        return prediction.copy(), receipt, {**logs, "runtime_sha256": builder._fingerprint(runtime)}
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        if name:
            shutil.rmtree(parent / name, ignore_errors=True)
        os.close(parent_fd)


def _macro_mse(losses: list[float]) -> float:
    if not losses or not all(map(math.isfinite, losses)):
        raise ValidationError("validation loss is non-finite or empty")
    return math.fsum(losses) / len(losses)


def _score(
    *,
    truth: np.ndarray,
    condition_records: list[dict[str, Any]],
    queries: list[tuple[str, ...]],
    seed_predictions: np.ndarray,
    eligible: set[str],
    gates: dict[str, Any],
) -> dict[str, Any]:
    if seed_predictions.shape != (3, len(queries), truth.shape[1]):
        raise ValidationError("seed prediction shape changed")
    query_position = {value: index for index, value in enumerate(queries)}
    aggregate = np.sum(seed_predictions, axis=0, dtype=np.float64) / 3.0
    aggregate_predictions = []
    routes = []
    for record in condition_records:
        targets = tuple(record["targets"])
        if not set(targets).issubset(eligible):
            raise ValidationError("Golden validation contains a non-native GEARS target")
        value = aggregate[query_position[targets]]
        route = "gears_three_seed_mean"
        aggregate_predictions.append(np.asarray(value, dtype=np.float64))
        routes.append(route)
    predicted = np.stack(aggregate_predictions)
    squared = np.square(predicted - truth, dtype=np.float64)
    condition_losses = np.sum(squared, axis=1, dtype=np.float64) / truth.shape[1]
    if not np.isfinite(condition_losses).all():
        raise ValidationError("aggregate validation loss is non-finite")
    per_condition = []
    by_scope: dict[str, list[float]] = {"single": [], "combination": []}
    for record, route, loss in zip(condition_records, routes, condition_losses, strict=True):
        value = float(loss)
        by_scope[record["scope"]].append(value)
        per_condition.append(
            {
                "condition_id": record["condition_id"],
                "targets": record["targets"],
                "scope": record["scope"],
                "route": route,
                "mse": value,
            }
        )
    aggregate_metrics = {
        "single_condition_macro_mse": _macro_mse(by_scope["single"]),
        "combination_condition_macro_mse": _macro_mse(by_scope["combination"]),
        "all_condition_macro_mse": _macro_mse(list(map(float, condition_losses))),
    }
    per_seed = []
    native_records = list(condition_records)
    for seed_index, seed in enumerate(_SEEDS):
        native_scope: dict[str, list[float]] = {"single": [], "combination": []}
        for record in native_records:
            row = query_position[tuple(record["targets"])]
            truth_row = truth[record["truth_row"]]
            difference = np.asarray(seed_predictions[seed_index, row], dtype=np.float64) - truth_row
            loss = float(np.sum(np.square(difference, dtype=np.float64), dtype=np.float64) / truth.shape[1])
            native_scope[record["scope"]].append(loss)
        per_seed.append(
            {
                "seed": seed,
                "native_condition_count": len(native_records),
                "native_single_condition_macro_mse": _macro_mse(native_scope["single"]),
                "native_combination_condition_macro_mse": _macro_mse(native_scope["combination"]),
            }
        )
    native_coverage = len(native_records) / len(condition_records)
    passed = bool(
        native_coverage == gates["native_scope_coverage"]
        and aggregate_metrics["single_condition_macro_mse"] < gates["single_condition_macro_mse_strictly_below"]
        and aggregate_metrics["combination_condition_macro_mse"]
        < gates["combination_condition_macro_mse_strictly_below"]
    )
    return {
        "metric": "condition_macro_full_feature_delta_mse",
        "feature_count": truth.shape[1],
        "reduction_dtype": "float64",
        "seed_aggregation": "elementwise_arithmetic_mean_in_seed_order_11_23_37",
        "native_scope_coverage": native_coverage,
        "native_condition_count": len(native_records),
        "fallback_condition_count": 0,
        "per_seed_native_scope": per_seed,
        "aggregate": aggregate_metrics,
        "per_condition": per_condition,
        "gate": {
            "single_condition_macro_mse_strictly_below": gates["single_condition_macro_mse_strictly_below"],
            "combination_condition_macro_mse_strictly_below": gates["combination_condition_macro_mse_strictly_below"],
            "validation_gate_passed": passed,
        },
    }


def evaluate(
    *,
    protocol_path: Path,
    prepare_root: Path,
    truth_bundle: Path,
    candidates_root: Path,
    output: Path,
) -> dict[str, Any]:
    protocol, base, builder = _load_protocol(protocol_path)
    _require_frozen(protocol)
    if os.path.lexists(output):
        raise ValidationError("output must be write-new")
    metadata, truth = _verify_truth_bundle(truth_bundle.absolute(), protocol, base, builder)
    _prepare_record, prepare_sha256, split, eligible = _verify_prepare_root(prepare_root, base, builder)
    if any(not set(record["targets"]).issubset(eligible) for record in metadata["conditions"]):
        raise ValidationError("Golden validation native coverage is not exactly 1.0")
    candidates = _verify_candidates(candidates_root.absolute(), protocol, base, builder, prepare_sha256)
    queries = sorted({tuple(record["targets"]) for record in metadata["conditions"]})
    predictions, child_receipt, runtime = _run_inference(
        prepare_root=prepare_root.absolute(),
        candidates=candidates,
        queries=queries,
        split=split,
        protocol=protocol,
        base=base,
        builder=builder,
        output_parent=output.absolute().parent,
    )
    metrics = _score(
        truth=truth,
        condition_records=metadata["conditions"],
        queries=queries,
        seed_predictions=predictions,
        eligible=eligible,
        gates=protocol["validation_gate"],
    )
    passed = metrics["gate"]["validation_gate_passed"]
    result = {
        "schema_version": "praxis.golden-gears-train-only-validation-result.v1",
        "record_role": "golden_validation_gate_result_not_test_not_scientific_promotion",
        "protocol_sha256": protocol["identity"]["payload_sha256"],
        "base_protocol_payload_sha256": base["identity"]["payload_sha256"],
        "evaluator_sha256": protocol["identity"]["evaluator_sha256"],
        "candidate_name": base["candidate"]["name"],
        "seeds": list(_SEEDS),
        "truth_bundle": protocol["truth_bundle"]["files"],
        "candidate_set": [
            {
                "seed": item["seed"],
                "candidate_record": item["candidate_record"],
                "model_pt": item["model_pt"],
                "tensor_manifest": item["tensor_manifest"],
            }
            for item in protocol["candidate_set"]["seeds"]
        ],
        "metrics": metrics,
        "execution": {
            "device": "cpu",
            "network_denied_by_sandbox": True,
            "full_golden_pack_received_by_evaluator": False,
            "validation_truth_bundle_used": True,
            "golden_test_expression_used": False,
            "golden_test_outcomes_used": False,
            "test_loader_present": False,
            "unsafe_config_pickle_read": False,
            "weights_only_strict_state_load": True,
            "model_eval_and_inference_mode": True,
            "child_receipt_sha256": builder._fingerprint(child_receipt),
            **runtime,
        },
        "states": {
            "validation_gate_passed": passed,
            "future_separately_authorized_descriptive_test_eligible": passed,
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
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-validation")
    prepare.add_argument("--protocol", type=Path, default=_VALIDATION_PROTOCOL)
    prepare.add_argument("--pack-root", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("evaluate")
    run.add_argument("--protocol", type=Path, default=_VALIDATION_PROTOCOL)
    run.add_argument("--prepare-root", type=Path, required=True)
    run.add_argument("--truth-bundle", type=Path, required=True)
    run.add_argument("--candidates-root", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if arguments.command == "prepare-validation":
        prepare_validation(protocol_path=arguments.protocol, pack_root=arguments.pack_root, output=arguments.output)
    else:
        result = evaluate(
            protocol_path=arguments.protocol,
            prepare_root=arguments.prepare_root,
            truth_bundle=arguments.truth_bundle,
            candidates_root=arguments.candidates_root,
            output=arguments.output,
        )
        print(json.dumps(result["metrics"]["gate"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

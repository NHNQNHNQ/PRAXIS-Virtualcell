#!/usr/bin/env python3
"""Issue a technical-only deterministic replay receipt for frozen Candidate-2."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).parents[1]
_VALIDATION_PROTOCOL = _ROOT / "data/golden/norman_2019/additive_train_only_validation_protocol.json"
_EVALUATOR = _ROOT / "scripts/evaluate_golden_additive_train_only_validation.py"
_VALIDATION_PROTOCOL_FILE = {
    "size_bytes": 7280,
    "sha256": "12fc57aaadb23a37d034d1f807547cfbbaa35cbe23c71d00d4de19030e922d6a",
}
_EVALUATOR_FILE = {
    "size_bytes": 30710,
    "sha256": "1b26c46c7646caf7530dbe6bac81526008d9d75d07cd227b044ca2809df43aaf",
}
_CANDIDATE_NAME = "norman_additive_ridge_train_only_alpha_0_1"
_CANDIDATE_FILES = {
    "baseline.json",
    "candidate-record.json",
    "linear_coefficients.npy",
    "linear_intercept.npy",
}


class ReplayError(ValueError):
    """Fail-closed deterministic replay error."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fingerprint(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReplayError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _read_regular(path: Path) -> tuple[bytes, dict[str, Any], tuple[int, int]]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise ReplayError(f"cannot safely open regular file: {path.name}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ReplayError(f"file must be regular and single-link: {path.name}")
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)

        def stable(info):
            return (
                info.st_dev,
                info.st_ino,
                info.st_mode,
                info.st_nlink,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
            )

        if stable(before) != stable(after):
            raise ReplayError(f"file changed while being read: {path.name}")
    finally:
        os.close(descriptor)
    payload = b"".join(chunks)
    identity = {"size_bytes": len(payload), "sha256": _sha256(payload)}
    return payload, identity, (before.st_dev, before.st_ino)


def _json_object(payload: bytes, *, name: str, canonical: bool) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda item: (_ for _ in ()).throw(ReplayError(f"non-finite JSON: {item}")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplayError(f"invalid JSON object: {name}") from exc
    if not isinstance(value, dict):
        raise ReplayError(f"expected JSON object: {name}")
    if canonical and payload != _canonical_bytes(value) + b"\n":
        raise ReplayError(f"JSON is not canonical with one trailing newline: {name}")
    return value


def _load_protocol() -> dict[str, Any]:
    payload, identity, _ = _read_regular(_VALIDATION_PROTOCOL)
    evaluator_payload, evaluator_identity, _ = _read_regular(_EVALUATOR)
    if identity != _VALIDATION_PROTOCOL_FILE or evaluator_identity != _EVALUATOR_FILE:
        raise ReplayError("frozen validation protocol or evaluator file identity changed")
    protocol = _json_object(payload, name=_VALIDATION_PROTOCOL.name, canonical=False)
    protocol_copy = json.loads(_canonical_bytes(protocol))
    try:
        protocol_copy["identity"]["payload_sha256"] = None
    except (KeyError, TypeError) as exc:
        raise ReplayError("validation protocol identity is incomplete") from exc
    identity_record = protocol.get("identity", {})
    candidate = protocol.get("candidate_artifact", {})
    ceiling = protocol.get("claim_ceiling", {})
    if not (
        protocol.get("schema_version") == "praxis.golden-additive-train-only-validation-protocol.v1"
        and protocol.get("implementation_status") == "FROZEN_EXECUTABLE"
        and identity_record.get("payload_sha256") == _fingerprint(protocol_copy)
        and identity_record.get("evaluator_sha256") == _sha256(evaluator_payload)
        and candidate.get("status") == "FROZEN"
        and set(candidate.get("required_inventory", [])) == _CANDIDATE_FILES
        and set(candidate.get("files", {})) == _CANDIDATE_FILES
        and ceiling
        == {
            "output_schema_version": "praxis.golden-additive-train-only-validation-result.v1",
            "record_role": "exposed_reused_development_validation_not_independent_not_test_not_scientific_promotion",
            "independent": False,
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
        }
    ):
        raise ReplayError("frozen validation protocol contract changed")
    return protocol


def _candidate_inventory(root: Path) -> None:
    try:
        root_info = root.lstat()
        entries = list(root.iterdir())
    except OSError as exc:
        raise ReplayError("candidate root is unavailable") from exc
    if not stat.S_ISDIR(root_info.st_mode) or root.is_symlink():
        raise ReplayError("candidate root must be a regular directory")
    if {entry.name for entry in entries} != _CANDIDATE_FILES:
        raise ReplayError("candidate four-file inventory changed")
    if any(not stat.S_ISREG(entry.lstat().st_mode) for entry in entries):
        raise ReplayError("candidate inventory contains a non-regular file")


def _verify_candidate(root: Path, protocol: dict[str, Any]) -> tuple[list[str], np.ndarray, np.ndarray, dict[str, Any]]:
    _candidate_inventory(root)
    expected = protocol["candidate_artifact"]["files"]
    payloads: dict[str, bytes] = {}
    for name in sorted(_CANDIDATE_FILES):
        payload, identity, _ = _read_regular(root / name)
        if identity != expected[name]:
            raise ReplayError(f"frozen candidate file identity changed: {name}")
        payloads[name] = payload

    baseline = _json_object(payloads["baseline.json"], name="baseline.json", canonical=True)
    record = _json_object(payloads["candidate-record.json"], name="candidate-record.json", canonical=True)
    base_protocol_sha256 = protocol["identity"]["base_protocol_payload_sha256"]
    claims = {
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "registry_or_default_route_changed": False,
    }
    if not (
        record.get("candidate_name") == baseline.get("candidate_name") == _CANDIDATE_NAME
        and record.get("protocol_sha256") == base_protocol_sha256
        and all(record.get(key) == value for key, value in claims.items())
        and record.get("artifacts", {}).get("baseline.json") == expected["baseline.json"]
    ):
        raise ReplayError("candidate receipt identity or claim ceiling changed")

    inference = protocol["inference"]
    feature_ids = baseline.get("feature_ids")
    target_ids = baseline.get("target_ids")
    if not (
        isinstance(feature_ids, list)
        and all(isinstance(value, str) for value in feature_ids)
        and len(feature_ids) == len(set(feature_ids)) == inference["ordered_feature_count"]
        and _fingerprint(feature_ids) == inference["ordered_feature_ids_sha256"]
        and isinstance(target_ids, list)
        and all(isinstance(value, str) for value in target_ids)
        and len(target_ids) == len(set(target_ids)) == inference["target_axis_count"]
        and set(target_ids).issubset(feature_ids)
        and _fingerprint(target_ids) == inference["target_ids_sha256"]
    ):
        raise ReplayError("candidate feature or target axis changed")

    arrays = baseline.get("arrays", {})
    loaded: dict[str, np.ndarray] = {}
    for name in ("linear_coefficients.npy", "linear_intercept.npy"):
        specification = inference["arrays"][name]
        if not (
            arrays.get(name, {}).get("filename") == name
            and {key: arrays[name].get(key) for key in ("size_bytes", "sha256")} == expected[name]
            and arrays[name].get("shape") == specification["shape"]
            and arrays[name].get("dtype") == specification["dtype"] == "float64"
            and record.get("artifacts", {}).get(name) == arrays[name]
        ):
            raise ReplayError(f"candidate array metadata changed: {name}")
        try:
            value = np.load(io.BytesIO(payloads[name]), allow_pickle=False)
        except (OSError, ValueError) as exc:
            raise ReplayError(f"candidate array cannot be safely loaded: {name}") from exc
        if list(value.shape) != specification["shape"] or value.dtype.str != "<f8" or not np.isfinite(value).all():
            raise ReplayError(f"candidate array geometry or dtype changed: {name}")
        loaded[name] = np.asarray(value, dtype=np.float64)

    runtime = record.get("runtime")
    runtime_contract = protocol["runtime"]
    if not isinstance(runtime, dict) or _fingerprint(runtime) != runtime_contract["expected_probe_sha256"]:
        raise ReplayError("candidate runtime probe identity changed")
    return target_ids, loaded["linear_coefficients.npy"], loaded["linear_intercept.npy"], runtime


def _verify_result(
    path: Path,
    candidate_root: Path,
    protocol: dict[str, Any],
) -> tuple[bytes, dict[str, Any], tuple[int, int], dict[str, Any], dict[str, Any]]:
    payload, result_identity, inode = _read_regular(path)
    result = _json_object(payload, name=path.name, canonical=True)
    target_ids, coefficients, intercept, runtime = _verify_candidate(candidate_root, protocol)
    ceiling = protocol["claim_ceiling"]
    expected_runtime = {
        "source_runtime_environment_sha256": protocol["runtime"]["source_runtime_environment_sha256"],
        "runtime_probe_sha256": protocol["runtime"]["expected_probe_sha256"],
        "runtime_probe": runtime,
    }
    states = result.get("states", {})
    execution = result.get("execution", {})
    claims = {
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "registry_or_default_route_changed": False,
    }
    if not (
        result.get("schema_version") == ceiling["output_schema_version"]
        and result.get("record_role") == ceiling["record_role"]
        and result.get("protocol_sha256") == protocol["identity"]["payload_sha256"]
        and result.get("base_protocol_payload_sha256") == protocol["identity"]["base_protocol_payload_sha256"]
        and result.get("evaluator_sha256") == protocol["identity"]["evaluator_sha256"]
        and result.get("candidate_name") == _CANDIDATE_NAME
        and result.get("candidate_artifact") == protocol["candidate_artifact"]["files"]
        and result.get("truth_bundle") == protocol["truth_bundle"]["files"]
        and result.get("validation_evidence_class") == "exposed_reused_development_validation"
        and result.get("independent") is False
        and result.get("prospective_test_blinding") is False
        and execution.get("reduction_runtime") == expected_runtime
        and execution.get("golden_test_expression_used") is False
        and execution.get("golden_test_outcomes_used") is False
        and execution.get("network_used") is False
        and all(states.get(key) == value for key, value in claims.items())
        and states.get("independent_validation_passed") is False
        and states.get("future_separately_authorized_descriptive_test_eligible") is False
    ):
        raise ReplayError("development result identity, runtime, or claim ceiling changed")

    metrics = result.get("metrics", {})
    conditions = metrics.get("per_condition")
    if not (
        isinstance(conditions, list)
        and conditions
        and metrics.get("feature_count") == len(intercept)
        and metrics.get("condition_count") == len(conditions)
    ):
        raise ReplayError("development result request inventory is invalid")
    requests = []
    condition_ids: set[str] = set()
    for condition in conditions:
        condition_id = condition.get("condition_id") if isinstance(condition, dict) else None
        requested = condition.get("target_feature_ids") if isinstance(condition, dict) else None
        if not (
            isinstance(condition_id, str)
            and condition_id not in condition_ids
            and isinstance(requested, list)
            and len(requested) in {1, 2}
            and len(requested) == len(set(requested))
            and all(isinstance(value, str) for value in requested)
        ):
            raise ReplayError("development result contains an invalid replay request")
        condition_ids.add(condition_id)
        requests.append({"condition_id": condition_id, "target_feature_ids": requested})

    positions = {target_id: index for index, target_id in enumerate(target_ids)}
    prediction_rows = []
    for request in requests:
        prediction = intercept.copy()
        for target_id in request["target_feature_ids"]:
            if target_id in positions:
                prediction += coefficients[positions[target_id]]
        prediction_rows.append(prediction)
    predictions = np.asarray(np.stack(prediction_rows), dtype="<f8", order="C")
    request_payload = _canonical_bytes(requests)
    prediction_payload = predictions.tobytes(order="C")
    request_identity = {
        "count": len(requests),
        "size_bytes": len(request_payload),
        "sha256": _sha256(request_payload),
    }
    prediction_identity = {
        "shape": list(predictions.shape),
        "dtype": "float64_little_endian_c_order",
        "size_bytes": len(prediction_payload),
        "sha256": _sha256(prediction_payload),
    }
    return payload, result_identity, inode, request_identity, prediction_identity


def _write_new(output: Path, payload: bytes) -> None:
    output = output.absolute()
    parent = output.parent
    if output.name in {"", ".", ".."}:
        raise ReplayError("invalid output filename")
    try:
        parent_info = parent.lstat()
    except OSError as exc:
        raise ReplayError("output parent is unavailable") from exc
    if not stat.S_ISDIR(parent_info.st_mode) or parent.is_symlink():
        raise ReplayError("output parent must be a regular directory")
    parent_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    temporary = f".{output.name}.{os.getpid()}.{os.urandom(8).hex()}"
    descriptor = -1
    try:
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
        os.link(temporary, output.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
        os.unlink(temporary, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except FileExistsError as exc:
        raise ReplayError("output must be write-new") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)


def create_receipt(*, candidate_root: Path, first_result: Path, second_result: Path, output: Path) -> dict[str, Any]:
    protocol = _load_protocol()
    first = _verify_result(first_result.absolute(), candidate_root.absolute(), protocol)
    second = _verify_result(second_result.absolute(), candidate_root.absolute(), protocol)
    if first[2] == second[2]:
        raise ReplayError("replay results must be distinct regular file inodes")
    if first[0] != second[0] or first[1] != second[1]:
        raise ReplayError("replay result bytes are not identical")
    if first[3:] != second[3:]:
        raise ReplayError("replay request or prediction bytes are not identical")

    result_identity, request_identity, prediction_identity = first[1], first[3], first[4]
    common = {
        "result_identity": result_identity,
        "request_target_set_identity": request_identity,
        "prediction_identity": prediction_identity,
    }
    receipt = {
        "schema_version": "praxis.candidate-2-deterministic-replay-receipt.v1",
        "record_role": "deterministic_technical_reproducibility_only_not_benchmark_or_scientific_evidence",
        "candidate_name": _CANDIDATE_NAME,
        "candidate_artifact": protocol["candidate_artifact"]["files"],
        "evaluator_identity": {
            "protocol_file": _VALIDATION_PROTOCOL_FILE,
            "protocol_payload_sha256": protocol["identity"]["payload_sha256"],
            "evaluator_file": _EVALUATOR_FILE,
        },
        "replays": [
            {"replay_id": "replay-1", **common},
            {"replay_id": "replay-2", **common},
        ],
        "verification": {
            "replay_ids_are_stochastic_seeds": False,
            "distinct_regular_single_link_result_inodes": True,
            "exact_result_bytes_identical": True,
            "exact_request_target_set_bytes_identical": True,
            "exact_prediction_bytes_identical": True,
            "process_provenance_not_inferred_from_equal_bytes": True,
            "deterministic_technical_replay_passed": True,
        },
        "states": {
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
            "registry_or_default_route_changed": False,
        },
    }
    _write_new(output, _canonical_bytes(receipt) + b"\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--first-result", type=Path, required=True)
    parser.add_argument("--second-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    receipt = create_receipt(
        candidate_root=arguments.candidate_root,
        first_result=arguments.first_result,
        second_result=arguments.second_result,
        output=arguments.output,
    )
    print(json.dumps(receipt["verification"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

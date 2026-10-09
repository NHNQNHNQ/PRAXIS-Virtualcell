from __future__ import annotations

import errno
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

_SCRIPT = Path(__file__).parents[2] / "scripts/replay_additive_candidate_determinism.py"


def _module():
    spec = importlib.util.spec_from_file_location("replay_additive_candidate_determinism", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(module, path: Path, value: dict) -> None:
    path.write_bytes(module._canonical_bytes(value) + b"\n")


def _identity(module, path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {"size_bytes": len(payload), "sha256": module._sha256(payload)}


def test_two_distinct_results_replay_to_exact_candidate_prediction_bytes(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    coefficients = np.asarray([[1.0, 2.0, 3.0], [-1.0, 4.0, 0.25]], dtype="<f8")
    intercept = np.asarray([0.5, -0.5, 1.5], dtype="<f8")
    np.save(candidate / "linear_coefficients.npy", coefficients, allow_pickle=False)
    np.save(candidate / "linear_intercept.npy", intercept, allow_pickle=False)
    coefficient_identity = _identity(module, candidate / "linear_coefficients.npy")
    intercept_identity = _identity(module, candidate / "linear_intercept.npy")
    array_records = {
        "linear_coefficients.npy": {
            "filename": "linear_coefficients.npy",
            **coefficient_identity,
            "shape": [2, 3],
            "dtype": "float64",
        },
        "linear_intercept.npy": {
            "filename": "linear_intercept.npy",
            **intercept_identity,
            "shape": [3],
            "dtype": "float64",
        },
    }
    feature_ids = ["t0", "t1", "f2"]
    target_ids = ["t0", "t1"]
    baseline = {
        "candidate_name": module._CANDIDATE_NAME,
        "feature_ids": feature_ids,
        "target_ids": target_ids,
        "arrays": array_records,
    }
    _write_json(module, candidate / "baseline.json", baseline)
    baseline_identity = _identity(module, candidate / "baseline.json")
    runtime = {"python": "fixture", "packages": {"numpy": np.__version__}}
    record = {
        "candidate_name": module._CANDIDATE_NAME,
        "protocol_sha256": "base-protocol-sha",
        "runtime": runtime,
        "artifacts": {"baseline.json": baseline_identity, **array_records},
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "registry_or_default_route_changed": False,
    }
    _write_json(module, candidate / "candidate-record.json", record)
    for sidecar in candidate.glob("._*"):
        sidecar.unlink()
    candidate_files = {
        "baseline.json": baseline_identity,
        "candidate-record.json": _identity(module, candidate / "candidate-record.json"),
        "linear_coefficients.npy": coefficient_identity,
        "linear_intercept.npy": intercept_identity,
    }

    evaluator = tmp_path / "evaluator.py"
    evaluator.write_bytes(b"# frozen fixture evaluator\n")
    evaluator_identity = _identity(module, evaluator)
    protocol = {
        "schema_version": "praxis.golden-additive-train-only-validation-protocol.v1",
        "implementation_status": "FROZEN_EXECUTABLE",
        "identity": {
            "payload_sha256": None,
            "base_protocol_payload_sha256": "base-protocol-sha",
            "evaluator_sha256": evaluator_identity["sha256"],
        },
        "candidate_artifact": {
            "status": "FROZEN",
            "required_inventory": sorted(candidate_files),
            "files": candidate_files,
        },
        "truth_bundle": {"files": {"metadata.json": {"size_bytes": 1, "sha256": "truth-id"}}},
        "runtime": {
            "source_runtime_environment_sha256": "runtime-environment-sha",
            "expected_probe_sha256": module._fingerprint(runtime),
        },
        "inference": {
            "ordered_feature_count": 3,
            "ordered_feature_ids_sha256": module._fingerprint(feature_ids),
            "target_axis_count": 2,
            "target_ids_sha256": module._fingerprint(target_ids),
            "arrays": {
                "linear_coefficients.npy": {"shape": [2, 3], "dtype": "float64"},
                "linear_intercept.npy": {"shape": [3], "dtype": "float64"},
            },
        },
        "claim_ceiling": {
            "output_schema_version": "praxis.golden-additive-train-only-validation-result.v1",
            "record_role": ("exposed_reused_development_validation_not_independent_not_test_not_scientific_promotion"),
            "independent": False,
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
        },
    }
    protocol["identity"]["payload_sha256"] = module._fingerprint(protocol)
    protocol_path = tmp_path / "protocol.json"
    _write_json(module, protocol_path, protocol)
    monkeypatch.setattr(module, "_VALIDATION_PROTOCOL", protocol_path)
    monkeypatch.setattr(module, "_VALIDATION_PROTOCOL_FILE", _identity(module, protocol_path))
    monkeypatch.setattr(module, "_EVALUATOR", evaluator)
    monkeypatch.setattr(module, "_EVALUATOR_FILE", evaluator_identity)

    expected_runtime = {
        "source_runtime_environment_sha256": "runtime-environment-sha",
        "runtime_probe_sha256": module._fingerprint(runtime),
        "runtime_probe": runtime,
    }
    states = {
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "registry_or_default_route_changed": False,
    }
    result_states = {
        **states,
        "independent_validation_passed": False,
        "future_separately_authorized_descriptive_test_eligible": False,
    }
    conditions = [
        {"condition_id": "request-1", "target_feature_ids": ["t0"]},
        {"condition_id": "request-2", "target_feature_ids": ["t0", "not-on-axis"]},
        {"condition_id": "request-3", "target_feature_ids": ["t1", "t0"]},
    ]
    result = {
        "schema_version": protocol["claim_ceiling"]["output_schema_version"],
        "record_role": protocol["claim_ceiling"]["record_role"],
        "protocol_sha256": protocol["identity"]["payload_sha256"],
        "base_protocol_payload_sha256": "base-protocol-sha",
        "evaluator_sha256": evaluator_identity["sha256"],
        "candidate_name": module._CANDIDATE_NAME,
        "candidate_artifact": candidate_files,
        "truth_bundle": protocol["truth_bundle"]["files"],
        "validation_evidence_class": "exposed_reused_development_validation",
        "independent": False,
        "prospective_test_blinding": False,
        "execution": {
            "reduction_runtime": expected_runtime,
            "golden_test_expression_used": False,
            "golden_test_outcomes_used": False,
            "network_used": False,
        },
        "metrics": {"feature_count": 3, "condition_count": 3, "per_condition": conditions},
        "states": result_states,
    }
    first_result = tmp_path / "result-1.json"
    second_result = tmp_path / "result-2.json"
    _write_json(module, first_result, result)
    _write_json(module, second_result, result)

    captured: dict[str, object] = {}

    def capture(output: Path, payload: bytes) -> None:
        captured.update(output=output, payload=payload)

    monkeypatch.setattr(module, "_write_new", capture)
    output = tmp_path / "receipt.json"
    receipt = module.create_receipt(
        candidate_root=candidate,
        first_result=first_result,
        second_result=second_result,
        output=output,
    )
    expected_predictions = np.asarray(
        [intercept + coefficients[0], intercept + coefficients[0], intercept + coefficients[1] + coefficients[0]],
        dtype="<f8",
        order="C",
    )
    assert receipt["replays"][0]["prediction_identity"] == receipt["replays"][1]["prediction_identity"]
    assert receipt["replays"][0]["prediction_identity"]["sha256"] == module._sha256(
        expected_predictions.tobytes(order="C")
    )
    assert receipt["verification"]["replay_ids_are_stochastic_seeds"] is False
    assert receipt["verification"]["deterministic_technical_replay_passed"] is True
    assert receipt["states"] == states
    assert captured == {"output": output, "payload": module._canonical_bytes(receipt) + b"\n"}
    assert not output.exists()

    changed_result = tmp_path / "result-changed.json"
    changed = json.loads(module._canonical_bytes(result))
    changed["metrics"]["per_condition"].reverse()
    _write_json(module, changed_result, changed)
    with pytest.raises(module.ReplayError, match="result bytes are not identical"):
        module.create_receipt(
            candidate_root=candidate,
            first_result=first_result,
            second_result=changed_result,
            output=tmp_path / "unused-receipt.json",
        )


def test_write_new_is_atomic_or_fails_closed_on_current_filesystem(tmp_path: Path) -> None:
    module = _module()
    output = tmp_path / "receipt.json"
    payload = b"receipt\n"
    try:
        module._write_new(output, payload)
    except OSError as exc:
        assert exc.errno in {errno.ENOTSUP, errno.EOPNOTSUPP}
        assert not output.exists()
    else:
        assert output.read_bytes() == payload
        with pytest.raises(module.ReplayError, match="write-new"):
            module._write_new(output, b"replacement\n")
        assert output.read_bytes() == payload
    assert not list(tmp_path.glob(".receipt.json.*"))
    assert not list(tmp_path.glob("._.receipt.json.*"))

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).parents[1]
_EVALUATOR_PATH = _ROOT / "scripts/evaluate_golden_gears_train_only_validation.py"
_PROTOCOL_PATH = _ROOT / "data/golden/norman_2019/gears_train_only_validation_protocol.json"
_RESULT_PATH = _ROOT / "reports/science/golden-gears-linux-a100-validation-result.json"


def _evaluator():
    spec = importlib.util.spec_from_file_location("golden_gears_validation_evaluator", _EVALUATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_control_sampling_known_answer_is_query_local_and_big_endian() -> None:
    module = _evaluator()
    builder = module._builder()
    indices, digest = module._control_indices(11, ("A", "B"), builder)
    assert indices[:10].tolist() == [1022, 1419, 1896, 289, 1635, 912, 1389, 1929, 995, 667]
    assert builder._fingerprint(indices.tolist()) == "80d27ccfdb5446a7fef2fd2935c888046e7184b43272856cc62409fcf00ada12"
    assert module._array_sha256(indices, ">u8") == "2544fc41f4adebf13d6b16ebb38b9ee92c72a23083744c405631312c15684878"
    assert digest == "ea5684f2744a018fda987e88bd92b43a959b796688aaaba5798852d548b0da90"
    assert module._control_indices(11, ("A", "B"), builder)[0].tolist() == indices.tolist()
    assert module._control_indices(23, ("A", "B"), builder)[0].tolist() != indices.tolist()


def test_validation_score_is_three_seed_float64_mean_with_zero_fallback() -> None:
    module = _evaluator()
    truth = np.zeros((2, 2), dtype=np.float64)
    records = [
        {"condition_id": "A+ctrl", "targets": ["A"], "scope": "single", "truth_row": 0},
        {"condition_id": "A+B", "targets": ["A", "B"], "scope": "combination", "truth_row": 1},
    ]
    predictions = np.asarray(
        [
            [[1.0, 1.0], [2.0, 2.0]],
            [[2.0, 2.0], [3.0, 3.0]],
            [[3.0, 3.0], [4.0, 4.0]],
        ],
        dtype=np.float64,
    )
    result = module._score(
        truth=truth,
        condition_records=records,
        queries=[("A",), ("A", "B")],
        seed_predictions=predictions,
        eligible={"A", "B"},
        gates={
            "native_scope_coverage": 1.0,
            "single_condition_macro_mse_strictly_below": 5.0,
            "combination_condition_macro_mse_strictly_below": 10.0,
        },
    )
    assert result["aggregate"] == {
        "single_condition_macro_mse": 4.0,
        "combination_condition_macro_mse": 9.0,
        "all_condition_macro_mse": 6.5,
    }
    assert result["fallback_condition_count"] == 0
    assert result["native_scope_coverage"] == 1.0
    assert result["gate"]["validation_gate_passed"] is True
    assert {item["route"] for item in result["per_condition"]} == {"gears_three_seed_mean"}


def test_validation_fails_closed_instead_of_using_fallback() -> None:
    module = _evaluator()
    with pytest.raises(module.ValidationError, match="non-native"):
        module._score(
            truth=np.zeros((2, 2), dtype=np.float64),
            condition_records=[
                {"condition_id": "A+ctrl", "targets": ["A"], "scope": "single", "truth_row": 0},
                {"condition_id": "A+B", "targets": ["A", "B"], "scope": "combination", "truth_row": 1},
            ],
            queries=[("A",), ("A", "B")],
            seed_predictions=np.zeros((3, 2, 2), dtype=np.float64),
            eligible={"A"},
            gates={
                "native_scope_coverage": 1.0,
                "single_condition_macro_mse_strictly_below": 1.0,
                "combination_condition_macro_mse_strictly_below": 1.0,
            },
        )


def test_candidate_inventory_requires_seven_files_and_collection_receipt() -> None:
    module = _evaluator()
    assert module._MODEL_FILES == {
        "candidate-record.json",
        "training.log",
        "model/config.pkl",
        "model/model.pt",
        "model/runtime-graph-manifest.json",
        "model/safe-config.json",
        "model/tensor-manifest.json",
    }
    source = _EVALUATOR_PATH.read_text(encoding="utf-8")
    assert 'root / "collection-record.json"' in source
    assert "candidate_runtime_graph_manifest" in source
    assert "raw_graph_manifest" in source
    assert "linux_a100_manifest_v1" in source
    assert "network_isolation_argv" in source
    assert "sandbox-exec" not in source


def test_candidate_inventory_and_nonexecuted_files_reject_link_or_drift(
    tmp_path: Path,
) -> None:
    module = _evaluator()
    builder = module._builder()
    candidate = tmp_path / "seed-11"
    model = candidate / "model"
    model.mkdir(parents=True)
    config = model / "config.pkl"
    training_log = candidate / "training.log"
    config.write_bytes(b"opaque pickle bytes")
    training_log.write_bytes(b"training log")
    record = {
        "artifacts": {
            "config.pkl": {
                **builder._file_record(config, single_link=True),
                "unsafe_pickle": True,
            },
            "training.log": builder._file_record(training_log, single_link=True),
        }
    }
    module._verify_nonexecuted_candidate_files(candidate, record, builder)
    training_log.write_bytes(b"changed")
    with pytest.raises(module.ValidationError, match="artifact identity"):
        module._verify_nonexecuted_candidate_files(candidate, record, builder)

    linked_root = tmp_path / "linked"
    linked_root.mkdir()
    source = linked_root / "source"
    source.write_bytes(b"same inode")
    os.link(source, linked_root / "alias")
    with pytest.raises(module.ValidationError, match="linked file"):
        module._regular_inventory(linked_root)


def test_truth_builder_only_indexes_validation_expression() -> None:
    source = _EVALUATOR_PATH.read_text(encoding="utf-8")
    start = source.index("def _validation_truth(")
    stop = source.index("\ndef prepare_validation(", start)
    body = source[start:stop]
    assert 'split == "validation"' in body
    assert "source.X[validation_positions]" not in body
    assert "source.X[positions]" in body
    assert '"decoded_expression_partitions": ["validation"]' in body
    assert '"test_expression_decoded": False' in body
    assert '"test_outcomes_used": False' in body
    assert 'source.X[np.flatnonzero(split == "test")]' not in body


def test_frozen_linux_protocol_is_self_consistent() -> None:
    module = _evaluator()
    value = json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))
    assert value["identity"]["evaluator_path"] == "scripts/evaluate_golden_gears_train_only_validation.py"
    assert value["identity"]["evaluator_sha256"] == module._builder()._sha256(_EVALUATOR_PATH)
    assert value["truth_bundle"]["status"] == "FROZEN"
    assert value["truth_bundle"]["preparation_evaluator_sha256"] == (
        "60cfc2e6a91acb13198ea60bf2757c7cd32f836d742acdc9bc3bfd73d9c24156"
    )
    assert value["truth_bundle"]["preparation_evaluator_sha256"] != value["identity"]["evaluator_sha256"]
    assert value["candidate_set"]["status"] == "FROZEN"
    assert value["candidate_set"]["profile"] == "linux_a100_manifest_v1"
    assert value["implementation_status"] == "FROZEN_EXECUTABLE"
    module._require_frozen(value)


def test_linux_graph_and_collection_identities_are_exactly_frozen() -> None:
    value = json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))
    candidate_set = value["candidate_set"]
    assert candidate_set["collection_record"] == {
        "size_bytes": 6594,
        "sha256": "e45020c925e52a674363f928c51667687c29017819634be5a1224d07f703c3f9",
    }
    assert candidate_set["linux_run_manifest"] == {
        "path": "data/golden/norman_2019/gears_train_only_linux_a100_run.json",
        "size_bytes": 5704,
        "sha256": "acc2a41bd96c197ddb7645f1357804fa21359d8c39a2f56f8e55976dcbb38bea",
        "payload_sha256": "b73c5fcec272407060aa7548776aeff604f98758855a3e7f2e9524766196fc04",
        "worker_sha256": "1eb19686f48773ab2a33c04dffef98c662f10ae3194608904fb68bda156c2f8d",
    }
    graphs = value["inference"]["candidate_runtime_graph_manifest"]["graphs"]
    assert graphs["G_go"]["edge_index"]["sha256"] == (
        "6a4885fe8a2911b710711d57088dfaf3451848d8136b4e4fc8ee9dd1d30a33a1"
    )
    assert graphs["G_go"]["edge_weight"]["sha256"] == (
        "9d99cc9e7e2631ee1e968c257d16eb23a97603d507873a13447a3ab7c700271a"
    )
    assert graphs["G_coexpress"]["edge_index"]["sha256"] == (
        "901f62f365b1d47c583458d041901f404d3f062ba50e2c5117c95813494e90fb"
    )
    assert graphs["G_coexpress"]["edge_weight"]["sha256"] == (
        "d381186ee3fc61d5067bedc95bad536a0a23f4b41fee79ce4ed8bfee1c9e4941"
    )


def test_claim_ceiling_never_promotes_validation_result() -> None:
    value = json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))
    assert value["claim_ceiling"] == {
        "output_schema_version": "praxis.golden-gears-train-only-validation-result.v1",
        "record_role": "golden_validation_gate_result_not_test_not_scientific_promotion",
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
    }
    assert value["execution_boundary"]["evaluator_receives_full_golden_pack"] is False
    assert value["execution_boundary"]["test_is_not_implemented_or_executed_by_this_evaluator"] is True


def test_checked_in_linux_validation_failure_is_exact_and_arithmetically_closed() -> None:
    protocol = json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))
    result_bytes = _RESULT_PATH.read_bytes()
    assert hashlib.sha256(result_bytes).hexdigest() == (
        "7a1ed0310dda4c48b2850dfc3486ed0d0f1852e6370a9f5c3da8f3bf90fb846f"
    )
    result = json.loads(result_bytes)
    assert result["protocol_sha256"] == protocol["identity"]["payload_sha256"]
    assert result["evaluator_sha256"] == protocol["identity"]["evaluator_sha256"]
    metrics = result["metrics"]
    per_condition = metrics["per_condition"]
    singles = [item["mse"] for item in per_condition if item["scope"] == "single"]
    combinations = [item["mse"] for item in per_condition if item["scope"] == "combination"]
    assert (len(per_condition), len(singles), len(combinations)) == (30, 14, 16)
    assert metrics["aggregate"] == {
        "single_condition_macro_mse": math.fsum(singles) / len(singles),
        "combination_condition_macro_mse": math.fsum(combinations) / len(combinations),
        "all_condition_macro_mse": math.fsum(singles + combinations) / len(per_condition),
    }
    assert metrics["native_scope_coverage"] == 1.0
    assert metrics["fallback_condition_count"] == 0
    assert metrics["gate"]["validation_gate_passed"] is False
    assert result["states"] == {
        "validation_gate_passed": False,
        "future_separately_authorized_descriptive_test_eligible": False,
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "registry_or_default_route_changed": False,
    }
    assert result["execution"]["golden_test_expression_used"] is False
    assert result["execution"]["golden_test_outcomes_used"] is False

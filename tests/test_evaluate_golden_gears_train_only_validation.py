from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).parents[1]
_EVALUATOR_PATH = _ROOT / "scripts/evaluate_golden_gears_train_only_validation.py"
_PROTOCOL_PATH = _ROOT / "data/golden/norman_2019/gears_train_only_validation_protocol.json"


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


def test_pending_protocol_is_self_consistent_but_evaluation_is_disabled() -> None:
    module = _evaluator()
    value = json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))
    assert value["identity"]["evaluator_path"] == "scripts/evaluate_golden_gears_train_only_validation.py"
    assert value["identity"]["evaluator_sha256"] == module._builder()._sha256(_EVALUATOR_PATH)
    assert value["truth_bundle"]["status"] in {"PENDING_FREEZE", "FROZEN"}
    assert value["candidate_set"]["status"] in {"PENDING_FREEZE", "FROZEN"}
    if value["implementation_status"] != "FROZEN_EXECUTABLE":
        with pytest.raises(module.ValidationError, match="not frozen"):
            module._require_frozen(value)


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

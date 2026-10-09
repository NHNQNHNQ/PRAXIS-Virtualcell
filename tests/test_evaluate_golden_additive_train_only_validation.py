from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).parents[1]
_EVALUATOR_PATH = _ROOT / "scripts/evaluate_golden_additive_train_only_validation.py"
_PROTOCOL_PATH = _ROOT / "data/golden/norman_2019/additive_train_only_validation_protocol.json"
_REASON = "preexisting_test_report_accidentally_read_during_science_design_audit_but_not_used_for_candidate_selection"


def _evaluator():
    spec = importlib.util.spec_from_file_location("golden_additive_validation_evaluator", _EVALUATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _records() -> list[dict[str, object]]:
    return [
        {
            "condition_id": "A+ctrl",
            "targets": ["A"],
            "target_feature_ids": ["E1"],
            "scope": "single",
            "truth_row": 0,
        },
        {
            "condition_id": "A+B",
            "targets": ["A", "B"],
            "target_feature_ids": ["E1", "E2"],
            "scope": "combination",
            "truth_row": 1,
        },
    ]


def test_score_uses_intercept_seen_coefficients_and_zero_for_unseen_targets() -> None:
    module = _evaluator()
    result = module._score(
        truth=np.zeros((2, 2), dtype=np.float64),
        condition_records=_records(),
        target_ids=["E1"],
        target_symbols=["A"],
        coefficients=np.ones((1, 2), dtype=np.float64),
        intercept=np.zeros(2, dtype=np.float64),
        gates={
            "single_condition_macro_mse_strictly_below": 2.0,
            "combination_condition_macro_mse_strictly_below": 2.0,
        },
    )
    assert result["aggregate"] == {
        "single_condition_macro_mse": 1.0,
        "combination_condition_macro_mse": 1.0,
        "all_condition_macro_mse": 1.0,
    }
    assert result["conditions_with_unseen_targets"] == 1
    assert result["per_condition"][1]["unseen_targets"] == ["B"]
    assert result["per_condition"][1]["unseen_target_feature_ids"] == ["E2"]
    assert result["gate"]["development_validation_thresholds_passed"] is True


def test_score_gates_are_strict_and_target_mapping_fails_closed() -> None:
    module = _evaluator()
    arguments = {
        "truth": np.zeros((2, 2), dtype=np.float64),
        "condition_records": _records(),
        "target_ids": ["E1"],
        "target_symbols": ["A"],
        "coefficients": np.zeros((1, 2), dtype=np.float64),
        "intercept": np.ones(2, dtype=np.float64),
        "gates": {
            "single_condition_macro_mse_strictly_below": 1.0,
            "combination_condition_macro_mse_strictly_below": 1.0,
        },
    }
    result = module._score(**arguments)
    assert result["gate"]["development_validation_thresholds_passed"] is False
    arguments["condition_records"] = [
        {
            "condition_id": "A+ctrl",
            "targets": ["A"],
            "target_feature_ids": ["WRONG"],
            "scope": "single",
            "truth_row": 0,
        }
    ]
    arguments["truth"] = np.zeros((1, 2), dtype=np.float64)
    with pytest.raises(module.ValidationError, match="symbol-to-feature"):
        module._score(**arguments)


def test_candidate_inventory_rejects_links(tmp_path: Path) -> None:
    module = _evaluator()
    source = tmp_path / "source"
    source.write_bytes(b"candidate")
    (tmp_path / "alias").symlink_to(source)
    with pytest.raises(module.ValidationError, match="unsafe entry"):
        module._regular_inventory(tmp_path)


def test_frozen_protocol_discloses_adaptive_reuse_and_claim_ceiling() -> None:
    module = _evaluator()
    protocol = json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))
    loaded, base, builder = module._load_protocol(_PROTOCOL_PATH)
    assert loaded == protocol
    assert protocol["identity"]["base_protocol_payload_sha256"] == base["identity"]["payload_sha256"]
    assert protocol["implementation_status"] == "FROZEN_EXECUTABLE"
    assert protocol["candidate_artifact"]["status"] == "FROZEN"
    module._require_frozen(protocol)
    reuse = protocol["validation_reuse"]
    assert module._verify_reuse_disclosure(protocol, builder) == reuse
    assert reuse["validation_evidence_class"] == "exposed_reused_development_validation"
    assert reuse["independent"] is False
    assert reuse["access_round"] == 2
    assert reuse["prior_validation_result"]["sha256"] == (
        "7a1ed0310dda4c48b2850dfc3486ed0d0f1852e6370a9f5c3da8f3bf90fb846f"
    )
    assert reuse["candidate_model_class_selected_after_prior_golden_validation_failure"] is True
    assert reuse["decision_path_is_adaptive_to_prior_golden_validation_failure"] is True
    assert reuse["candidate_hyperparameters_selected_from_golden_validation_values"] is False
    assert reuse["candidate_hyperparameter_selection_source"] == (
        "frozen_train_only_93_condition_fit_11_condition_internal_validation_only"
    )
    assert reuse["prospective_test_blinding"] is False
    assert reuse["prospective_test_blinding_reason"] == _REASON
    changed = json.loads(json.dumps(protocol))
    changed["validation_reuse"]["prospective_test_blinding_reason"] = "undisclosed"
    with pytest.raises(module.ValidationError, match="reuse disclosure"):
        module._verify_reuse_disclosure(changed, builder)
    assert protocol["claim_ceiling"] == {
        "output_schema_version": "praxis.golden-additive-train-only-validation-result.v1",
        "record_role": "exposed_reused_development_validation_not_independent_not_test_not_scientific_promotion",
        "independent": False,
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
    }


def test_frozen_candidate_file_identities_are_exact() -> None:
    protocol = json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))
    assert protocol["candidate_artifact"]["files"] == {
        "baseline.json": {
            "size_bytes": 95109,
            "sha256": "70ce31dbdca35d0e9f530679b61163cf8dd6abd585fdb1b4af245a50d9c54150",
        },
        "candidate-record.json": {
            "size_bytes": 6165,
            "sha256": "743bc29d2659de8eb8ee51511937f8e4f4532d02fe89bc3a82ce4cae087e1518",
        },
        "linear_coefficients.npy": {
            "size_bytes": 2744608,
            "sha256": "b11e6555fb3cdcf626d74a6fc5ece181c6d0c7f92c45e2bd737689773c5fd426",
        },
        "linear_intercept.npy": {
            "size_bytes": 40488,
            "sha256": "6a68609d883ce01a764567a7eae8dd64e645d2b3cbdcab5db50d5c106a0e1cae",
        },
    }


def test_evaluator_accepts_no_pack_prepare_or_test_input() -> None:
    source = _EVALUATOR_PATH.read_text(encoding="utf-8")
    assert 'parser.add_argument("--truth-bundle"' in source
    assert 'parser.add_argument("--candidate-root"' in source
    assert 'parser.add_argument("--output"' in source
    assert '"--pack-root"' not in source
    assert '"--prepare-root"' not in source
    assert "prepare_validation(" not in source
    assert "verifier._verify_truth_bundle" in source
    assert '"golden_test_expression_used": False' in source
    assert '"golden_test_outcomes_used": False' in source
    assert '"future_separately_authorized_descriptive_test_eligible": False' in source
    evaluate_body = source[source.index("def evaluate(") : source.index("\ndef main(")]
    assert evaluate_body.index("runtime = _verify_runtime") < evaluate_body.index("_verify_truth_bundle")
    assert evaluate_body.index("runtime = _verify_runtime") < evaluate_body.index("_verify_candidate")


def test_protocol_pins_inherited_exact_reduction_runtime() -> None:
    protocol = json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))
    assert protocol["runtime"] == {
        "verification": (
            "reuse_frozen_GEARS_train_runner_exact_venv_parent_environment_module_origin_and_"
            "child_runtime_probe_before_any_truth_or_candidate_array_load"
        ),
        "source_base_protocol_payload_sha256": "58285f730f46dc7fe7f5aad752a80cb8d22184171ff9186fd93e4040280388ef",
        "source_builder_path": "scripts/build_golden_gears_train_only_candidate.py",
        "source_builder_sha256": "f6fff4f1585ba4ca0762de58aa758fba753fd55f2e9f16e23fd3288ab878cde6",
        "source_train_runner_path": "scripts/train_golden_gears_train_only_candidate.py",
        "source_train_runner_sha256": "635db2e12fcfaa1668414c8bc812e6a015ac95aea39640def3884b2e28ff6582",
        "source_runtime_environment_sha256": "2e8adb7845de2fdf397bc16503d797ecb2be8944bf99c752cc255278abe299f7",
        "expected_probe_sha256": "71d07b3becff583c2d24fc37e9eddedbf4851da870abbb01e343c0e9bd0cd4d3",
    }


def test_candidate_mapping_hash_uses_axis_ordered_id_symbol_records() -> None:
    source = _EVALUATOR_PATH.read_text(encoding="utf-8")
    assert '{"target_id": target_id, "symbol": symbol}' in source
    assert "target_id_symbol_pairs_sha256" in source
    assert "zip(target_ids, target_symbols, strict=True)" in source

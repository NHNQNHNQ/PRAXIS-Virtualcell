from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).parents[1]
_BUILDER_PATH = _ROOT / "scripts/build_golden_additive_train_only_candidate.py"
_PROTOCOL_PATH = _ROOT / "data/golden/norman_2019/additive_train_only_protocol.json"


def _builder():
    spec = importlib.util.spec_from_file_location("golden_additive_train_only_builder", _BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _protocol() -> dict:
    return json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_protocol_identity_claim_ceiling_and_exposure_are_frozen() -> None:
    module = _builder()
    value = _protocol()
    assert value["identity"]["builder_sha256"] == module._sha256(_BUILDER_PATH)
    copy = json.loads(module._canonical_bytes(value))
    copy["identity"]["payload_sha256"] = None
    assert value["identity"]["payload_sha256"] == module._fingerprint(copy)
    assert value["execution_boundary"]["output_inventory"] == [
        "baseline.json",
        "linear_coefficients.npy",
        "linear_intercept.npy",
        "candidate-record.json",
    ]
    assert value["claim_ceiling"] == {
        "output_schema_version": "praxis.golden-additive-train-only-candidate.v1",
        "output_record_role": "train_only_candidate_2_and_contamination_audit_not_scientific_evidence",
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
    }
    exposure = value["decision_path_exposure"]
    assert exposure["golden_validation_is_now_a_reused_development_set"] is True
    assert exposure["candidate_development_is_independent_of_golden_validation"] is False
    assert exposure["prior_existing_golden_test_report_accidentally_read_only_exposed_during_collaborative_audit"]
    assert exposure["prior_existing_golden_test_report_used_for_candidate_choice_parameters_or_gate"] is False
    assert exposure["prospective_test_blinding"] is False


def test_alpha_selection_requires_both_scope_improvements() -> None:
    module = _builder()
    rows = [
        {
            "alpha": 0.1,
            "single_condition_macro_mse": 1.0,
            "combination_condition_macro_mse": 2.0,
            "normalized_max_score": 0.5,
        },
        {
            "alpha": 1.0,
            "single_condition_macro_mse": 2.0,
            "combination_condition_macro_mse": 3.0,
            "normalized_max_score": 0.8,
        },
    ]
    assert module._choose_alpha(rows, 1.0)["alpha"] == 0.1
    rows[0]["combination_condition_macro_mse"] = 4.0
    with pytest.raises(module.CandidateBuildError, match="does not improve both"):
        module._choose_alpha(rows, 1.0)


def test_internal_validation_only_target_keeps_an_exact_zero_row() -> None:
    module = _builder()
    deltas = {
        "A+ctrl": np.array([1.0, 2.0], dtype=np.float64),
        "A+B": np.array([3.0, 5.0], dtype=np.float64),
    }
    coefficients, intercept, seen, unseen = module._fit(["A+ctrl", "A+B"], deltas, ["A", "B", "C"], 0.1)
    assert seen == ["A", "B"]
    assert unseen == ["C"]
    assert np.array_equal(coefficients[2], np.zeros(2, dtype=np.float64))
    assert coefficients.dtype == intercept.dtype == np.float64


def test_condition_sum_promotes_to_float64_before_reduction(tmp_path: Path) -> None:
    import anndata
    from scipy import sparse

    module = _builder()
    path = tmp_path / "rounding.h5ad"
    adata = anndata.AnnData(
        X=sparse.csr_matrix(np.array([[1e8], [1.0], [-1e8]], dtype=np.float32)),
        obs={"condition": ["ctrl", "ctrl", "ctrl"]},
    )
    adata.write_h5ad(path)
    means = module._condition_means(path, ["ctrl", "ctrl", "ctrl"], 1)
    assert means["ctrl"].dtype == np.float64
    assert means["ctrl"][0] == pytest.approx(1.0 / 3.0, rel=0.0, abs=1e-15)


def test_runtime_drift_fails_before_prepare_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _builder()
    monkeypatch.setattr(module, "_load_protocol", lambda _path: {"identity": {}})
    monkeypatch.setattr(module, "_load_base_protocol", lambda _protocol: {})

    def reject_runtime(_builder, _base):
        raise module.CandidateBuildError("runtime drift")

    monkeypatch.setattr(module._GEARS_TRAIN, "_verify_runtime", reject_runtime)
    monkeypatch.setattr(
        module,
        "_prepare_data",
        lambda *_args, **_kwargs: pytest.fail("prepare data read before runtime validation"),
    )
    with pytest.raises(module.CandidateBuildError, match="runtime drift"):
        module.build(prepare_root=tmp_path, output=tmp_path / "output")


def test_builder_has_no_golden_validation_or_test_input() -> None:
    source = _BUILDER_PATH.read_text(encoding="utf-8")
    assert "validation-truth" not in source
    assert "reports/science" not in source
    assert 'add_argument("--prepare-root"' in source
    assert 'add_argument("--output"' in source
    assert 'add_argument("--pack"' not in source

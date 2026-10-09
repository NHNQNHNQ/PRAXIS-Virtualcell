"""Task 6(W4b):真 predictor 端到端 communicative workflow —— trace/provenance + success/abstain。仅远端。"""
import hashlib
import json
import os
from pathlib import Path

import pytest

from praxis_virtualcell.governance.provenance_hash import check_call_provenance
from praxis_virtualcell.predictors.ml.checkpoint_identity import (
    ML_SLOT_CHECKPOINTS,
    checkpoint_model_version,
)

pytestmark = pytest.mark.remote

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def _checkpoint_dir() -> Path:
    """Validate the configured W4B checkpoint set before importing donor code."""
    raw = os.environ.get("W4B_CKPT_DIR")
    if not raw:
        pytest.skip("W4B_CKPT_DIR is not set; current-candidate remote ML validation is pending")

    ckpt_dir = Path(raw).expanduser()
    if not ckpt_dir.is_dir():
        pytest.fail(f"W4B_CKPT_DIR is not a directory: {ckpt_dir}", pytrace=False)

    required = [ckpt_dir / f"{stem}{suffix}"
                for stem, _class_name in ML_SLOT_CHECKPOINTS.values()
                for suffix in (".json", ".pt")]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        pytest.fail(
            f"W4B checkpoint set is incomplete; missing: {', '.join(missing)}",
            pytrace=False,
        )
    for slot, (stem, expected_class) in ML_SLOT_CHECKPOINTS.items():
        try:
            checkpoint_model_version(ckpt_dir / stem, expected_class=expected_class)
        except (OSError, ValueError) as exc:
            pytest.fail(
                f"W4B checkpoint identity is invalid for {slot}: {exc}",
                pytrace=False,
            )
    return ckpt_dir


@pytest.fixture(scope="module")
def ckpt_and_ds():
    ckpt_dir = _checkpoint_dir()
    try:
        from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

        dataset = load_norman(split="test", max_perts=2, max_cells=2)
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        pytest.fail(
            f"configured remote donor/data prerequisite is unavailable: {type(exc).__name__}: {exc}",
            pytrace=False,
        )
    return str(ckpt_dir), dataset


def _assert_gate_a_not_triggered(report: dict) -> None:
    provenance = report["provenance"]
    assert "provenance_hash_gate" not in provenance, report
    assert "incomplete_call_provenance" not in report.get("abstain_reasons", []), report


def _canonical_hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def _assert_used_call_provenance(
    report: dict, ckpt_dir: str, predictor_results: list[dict]
) -> None:
    """Every accepted real predictor must identify its checkpoint and complete Gate A."""
    _assert_gate_a_not_triggered(report)
    assert report["models_used"] == list(ML_SLOT_CHECKPOINTS), report
    provenance = report["provenance"]
    assert provenance["models_used"] == report["models_used"]
    per_call_hashes = provenance["per_call_hashes"]
    assert set(per_call_hashes) == set(report["models_used"]), per_call_hashes
    results_by_name = {result["agent_name"]: result for result in predictor_results}
    for model_name in report["models_used"]:
        per_call = per_call_hashes.get(model_name)
        assert check_call_provenance(per_call) == [], {model_name: per_call}
        assert per_call["model_name"] == model_name
        expected_version = checkpoint_model_version(
            Path(ckpt_dir) / ML_SLOT_CHECKPOINTS[model_name][0],
            expected_class=ML_SLOT_CHECKPOINTS[model_name][1],
        )
        assert per_call["model_version"] == expected_version
        assert per_call["output_hash"] == _canonical_hash(
            results_by_name[model_name]["prediction"]
        )
        for key in ("input_hash", "output_hash"):
            value = per_call[key]
            assert len(value) == 64 and set(value) <= set("0123456789abcdef")


def test_ml_workflow_human_success_with_trace(ckpt_and_ds):
    from praxis_virtualcell.core.request import VirtualCellRequest
    from praxis_virtualcell.workflows.predict_delta_expression_ml import build_runtime_ml

    ckpt, ds = ckpt_and_ds
    rt = build_runtime_ml(ckpt, norman_ds=ds)
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))

    assert report["abstain"] is False, report
    assert report["models_used"] == list(ML_SLOT_CHECKPOINTS), report
    assert report["models_rejected"] == [], report
    assert report["models_failed"] == [], report
    assert report.get("abstain_reasons", []) == [], report
    assert report["prediction"] is not None
    assert report["critic_violations"] == []
    # 真多智能体证据:retrieve-before-predict + 真 predictor 通讯 + provenance 全在 trace
    assert rt.bus.has_message_type("brain_retrieved")
    assert rt.bus.has_message_type("predictor_result")
    assert rt.bus.has_message_type("provenance_done")
    assert "provenance" in report
    predictor_results = [message.payload for message in rt.bus.trace
                         if message.message_type == "predictor_result"]
    assert len(predictor_results) == len(ML_SLOT_CHECKPOINTS), predictor_results
    assert [result["agent_name"] for result in predictor_results] == list(ML_SLOT_CHECKPOINTS)
    assert all(result["status"] == "success" for result in predictor_results), predictor_results
    _assert_used_call_provenance(report, ckpt, predictor_results)


def test_ml_workflow_bacteria_abstain(ckpt_and_ds):
    from praxis_virtualcell.core.request import VirtualCellRequest
    from praxis_virtualcell.workflows.predict_delta_expression_ml import build_runtime_ml

    ckpt, ds = ckpt_and_ds
    rt = build_runtime_ml(ckpt, norman_ds=ds)
    report = rt.run_workflow(VirtualCellRequest.from_dict(dict(_HUMAN, species="bacteria", request_id="r2")))

    assert report["abstain"] is True, report
    assert report["models_used"] == []
    assert report["models_rejected"] == list(ML_SLOT_CHECKPOINTS), report
    assert report["models_failed"] == [], report
    _assert_gate_a_not_triggered(report)

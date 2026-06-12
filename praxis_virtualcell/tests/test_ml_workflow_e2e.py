"""Task 6(W4b):真 predictor 端到端 communicative workflow —— trace/provenance + success/abstain。仅远端。"""
import os

import pytest

pytestmark = pytest.mark.remote

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


@pytest.fixture(scope="module")
def ckpt_and_ds():
    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

    return os.environ["W4B_CKPT_DIR"], load_norman(split="test", max_perts=2, max_cells=2)


def test_ml_workflow_human_success_with_trace(ckpt_and_ds):
    from praxis_virtualcell.core.request import VirtualCellRequest
    from praxis_virtualcell.workflows.predict_delta_expression_ml import build_runtime_ml

    ckpt, ds = ckpt_and_ds
    rt = build_runtime_ml(ckpt, norman_ds=ds)
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))

    assert report["abstain"] is False, report
    assert report["models_used"], report  # 至少一个真 predictor success
    assert report["prediction"] is not None
    assert report["critic_violations"] == []
    # 真多智能体证据:retrieve-before-predict + 真 predictor 通讯 + provenance 全在 trace
    assert rt.bus.has_message_type("brain_retrieved")
    assert rt.bus.has_message_type("predictor_result")
    assert rt.bus.has_message_type("provenance_done")
    assert "provenance" in report


def test_ml_workflow_bacteria_abstain(ckpt_and_ds):
    from praxis_virtualcell.core.request import VirtualCellRequest
    from praxis_virtualcell.workflows.predict_delta_expression_ml import build_runtime_ml

    ckpt, ds = ckpt_and_ds
    rt = build_runtime_ml(ckpt, norman_ds=ds)
    report = rt.run_workflow(VirtualCellRequest.from_dict(dict(_HUMAN, species="bacteria", request_id="r2")))

    assert report["abstain"] is True, report
    assert report["models_used"] == []

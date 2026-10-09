from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_llm_assisted_without_key_equals_offline():
    off = build_runtime(RuntimeConfig(mode=Mode.OFFLINE)).run_workflow(
        VirtualCellRequest.from_dict(_HUMAN))

    llm = build_runtime(RuntimeConfig(mode=Mode.LLM_ASSISTED, deepseek_api_key="")).run_workflow(
        VirtualCellRequest.from_dict(_HUMAN))
    for k in ("abstain", "prediction", "models_used", "models_rejected", "reliability"):
        assert off[k] == llm[k]
    assert "narrative" not in llm

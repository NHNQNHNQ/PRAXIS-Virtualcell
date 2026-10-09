import os

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


@pytest.mark.llm
def test_structured_fields_identical_offline_vs_llm_assisted():
    load_env()
    off = build_runtime(RuntimeConfig(mode=Mode.OFFLINE)).run_workflow(
        VirtualCellRequest.from_dict(_HUMAN))
    cfg = RuntimeConfig(mode=Mode.LLM_ASSISTED, deepseek_api_key=os.environ["DEEPSEEK_API_KEY"])
    llm = build_runtime(cfg).run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    for k in ("abstain", "prediction", "models_used", "models_rejected",
              "reliability", "abstain_reasons", "critic_violations"):
        assert off[k] == llm[k], f"Field {k} changed under llm_assisted"
    assert "narrative" in llm
    assert "llm_route_suggestion" in llm["provenance"]

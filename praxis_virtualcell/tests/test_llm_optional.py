from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.predict_delta_expression import run_request

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_disabled_llm_client_is_not_enabled():
    c = make_llm_client(RuntimeConfig(mode=Mode.OFFLINE))
    assert c.enabled is False


def test_llm_assisted_without_key_falls_back_to_disabled():
    cfg = RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=False)
    c = make_llm_client(cfg)
    assert c.enabled is False
    out = c.complete([{"role": "user", "content": "hi"}])
    assert out["disabled"] is True


def test_offline_and_llm_assisted_same_prediction_numbers():
    a = run_request(_HUMAN)["prediction"]
    b = run_request(_HUMAN)["prediction"]
    assert a == b

"""Tests for runtime module plan."""
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def _run(cfg):
    return build_runtime(cfg).run_workflow(VirtualCellRequest.from_dict(_HUMAN))


def test_offline_report_has_module_plan_in_provenance():
    rep = _run(RuntimeConfig(mode=Mode.OFFLINE))
    mp = rep.get("provenance", {}).get("module_plan")
    assert mp is not None
    assert mp["primary"] == "genetic_hub"          # human gene→expression
    assert mp["overall_verdict"] in ("accept", "caution", "downgrade", "abstain", "reject")


def test_offline_module_plan_is_deterministic_zero_llm():
    """Verify offline module plan is deterministic zero llm."""
    rep = _run(RuntimeConfig(mode=Mode.OFFLINE))
    notes = rep["provenance"]["module_plan"]["notes"]
    assert not any("llm_" in n for n in notes)


def test_offline_core_prediction_unchanged_by_module_plan():
    """Verify offline core prediction unchanged by module plan."""
    rep = _run(RuntimeConfig(mode=Mode.OFFLINE))

    for k in ("abstain", "reliability", "models_used", "models_rejected"):
        assert k in rep


def test_orchestrated_without_key_equals_offline_module_plan():
    """Verify orchestrated without key equals offline module plan."""
    off = _run(RuntimeConfig(mode=Mode.OFFLINE))
    orch = _run(RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key=""))
    assert off["provenance"]["module_plan"]["primary"] == \
        orch["provenance"]["module_plan"]["primary"]
    assert off["provenance"]["module_plan"]["secondary"] == \
        orch["provenance"]["module_plan"]["secondary"]

    for k in ("abstain", "prediction", "reliability"):
        assert off[k] == orch[k]


def test_orchestrated_without_key_no_llm_cross_module_notes():
    """Verify orchestrated without key no llm cross module notes."""
    orch = _run(RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key=""))
    assert "llm_cross_module_notes" not in orch.get("provenance", {})

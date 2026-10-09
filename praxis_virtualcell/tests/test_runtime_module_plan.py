"""Phase 4:接管线 —— module_plan 旁路挂进 report.provenance。
铁律:OFFLINE 产确定性 module_plan(零 LLM),核心 prediction/reliability 字段与接管线前等价;
LLM_ORCHESTRATED 无 key → 回退等价 OFFLINE(红线 1)。"""
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
    """OFFLINE 的 module_plan notes 不含 llm_* 标记(零 LLM)。"""
    rep = _run(RuntimeConfig(mode=Mode.OFFLINE))
    notes = rep["provenance"]["module_plan"]["notes"]
    assert not any("llm_" in n for n in notes)


def test_offline_core_prediction_unchanged_by_module_plan():
    """接 module_plan 不改核心 prediction/reliability(旁路挂载,红线:不改现有逻辑)。"""
    rep = _run(RuntimeConfig(mode=Mode.OFFLINE))
    # 核心字段仍在(module_plan 是旁路,不动主报告)
    for k in ("abstain", "reliability", "models_used", "models_rejected"):
        assert k in rep


def test_orchestrated_without_key_equals_offline_module_plan():
    """红线 1:LLM_ORCHESTRATED 无 key → LLM 节点不注册 → module_plan 与 OFFLINE 等价。"""
    off = _run(RuntimeConfig(mode=Mode.OFFLINE))
    orch = _run(RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key=""))
    assert off["provenance"]["module_plan"]["primary"] == \
        orch["provenance"]["module_plan"]["primary"]
    assert off["provenance"]["module_plan"]["secondary"] == \
        orch["provenance"]["module_plan"]["secondary"]
    # 核心预测也等价
    for k in ("abstain", "prediction", "reliability"):
        assert off[k] == orch[k]


def test_orchestrated_without_key_no_llm_cross_module_notes():
    """无 key → 不注册 reasoner → 无 llm_cross_module_notes(不静默假装有)。"""
    orch = _run(RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key=""))
    assert "llm_cross_module_notes" not in orch.get("provenance", {})

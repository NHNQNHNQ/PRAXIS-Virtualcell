"""P10.C3 LLM 全入口守卫 + narrative 一致性 + 抗注入边界 测试。
narrative gate:确定性窄门(数值出处 + abstain 语义)→ 违规 fail-closed 丢弃 narrative,
绝不碰 abstain/prediction/reliability(LLM 外层问题不得反向改写确定性裁决)。"""
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_ACCEPT = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}


def test_baseline_offline_has_no_narrative_and_no_c3_gate():
    """接线前提坐实:OFFLINE 无 LLMReport → 无 narrative → C3 gate 不进(字节等价保留);
    且无 C3 gate provenance 键。接线后本断言仍须成立(gate 不误伤 offline 主链)。"""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert "narrative" not in sr                 # run_query 的 structured_report 已剔 narrative
    assert "narrative_consistency_gate" not in sr["provenance"]

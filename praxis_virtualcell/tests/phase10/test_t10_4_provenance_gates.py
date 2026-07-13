"""P10.C2 provenance 完整性硬门 + per-call hash + 越界 cell type abstain 测试。
三 gate 全 C1 模式(runtime 后处理 override,不碰 reliability/critic 裁决数值)。"""
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_ACCEPT = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}


def test_baseline_accept_report_healthy():
    """接线前提坐实:正常 accept 请求 abstain=False + provenance 基础字段齐。
    接线后三 gate 设计为对一致/正常请求不触发,本断言仍须成立(gate 不误伤)。"""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is False
    prov = sr["provenance"]
    for f in ("rules_referenced", "models_used", "n_messages"):
        assert f in prov, f"provenance 缺基础字段 {f}"

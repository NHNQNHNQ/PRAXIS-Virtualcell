"""Phase 5:接管线 —— evidence_level + learning_queue 旁路挂 report.provenance(插点 C/D)。
OFFLINE 零 LLM;不改 prediction/裁决;无 evidence/AL agent 时不挂(gated)。"""
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "al_ahr", "species": "human", "cell_type": "K562",
          "perturbation_type": "gene", "perturbation_targets": ["AHR"],
          "task_type": "predict_delta_expression",
          "input_modality": "scRNA", "output_modality": "delta_expression"}


def test_offline_report_has_evidence_level_and_learning_queue():
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    prov = report["provenance"]
    assert "evidence_level" in prov
    assert prov["evidence_level"]["level"].startswith("E")
    assert "learning_queue" in prov
    assert "items" in prov["learning_queue"]


def test_offline_registers_evidence_and_al_agents_zero_llm():
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    ns = set(rt._agents)
    assert "EvidenceLevelAgent" in ns and "ActiveLearningAgent" in ns
    # OFFLINE 零 LLM:无任何 LLM 节点
    assert not any(n.startswith("LLM") for n in ns), ns


def test_evidence_level_does_not_change_prediction_or_verdict():
    """插点 C/D 不改 prediction/abstain/reliability(advisory 不碰裁决)。"""
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    # 与不接主动学习的核心字段一致性:prediction 由 ensemble 定,abstain=False(有效 human gene 请求)
    assert report["abstain"] is False
    assert report["reliability"] in ("high", "medium", "low")
    assert report["prediction"] is not None


def test_learning_queue_reads_evidence_level():
    """AL 读到 evidence_level(证据等级进 AL 排序信号)。"""
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    q = report["provenance"]["learning_queue"]
    # 有 module_plan(Phase 4 已挂)→ 有候选
    assert isinstance(q["items"], list)
    assert "genetic_hub@human:AHR" in {item["candidate"] for item in q["items"]}


def test_abstain_request_evidence_e0_e1_no_accept():
    """空 perturbation_targets → abstain → evidence E0/E1,不被抬成 accept 级。"""
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    req = dict(_HUMAN, request_id="noab", perturbation_targets=[])
    report = rt.run_workflow(VirtualCellRequest.from_dict(req))
    assert report["abstain"] is True
    assert report["provenance"]["evidence_level"]["level"] in ("E0", "E1")

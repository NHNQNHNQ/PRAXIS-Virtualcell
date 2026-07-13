"""P10.C2 provenance 完整性硬门 + per-call hash + 越界 cell type abstain 测试。
三 gate 全 C1 模式(runtime 后处理 override,不碰 reliability/critic 裁决数值)。"""
import hashlib
import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.governance.gate_util import apply_governance_gate
from praxis_virtualcell.governance.provenance_completeness import check_report_provenance
from praxis_virtualcell.governance.provenance_hash import check_call_provenance, compute_call_provenance
from praxis_virtualcell.predictors.base import PredictorAgent
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


def test_compute_call_provenance_deterministic():
    a = compute_call_provenance("MockLinear", "mock:MockLinear", {"targets": ["AHR"]},
                                {"delta": [0.0]}, ["mock"])
    b = compute_call_provenance("MockLinear", "mock:MockLinear", {"targets": ["AHR"]},
                                {"delta": [0.0]}, ["mock"])
    assert a == b
    assert set(a) == {"model_name", "model_version", "input_hash", "output_hash", "evidence_source"}
    assert a["model_name"] == "MockLinear"
    assert a["model_version"] == "mock:MockLinear"
    assert len(a["input_hash"]) == 64 and len(a["output_hash"]) == 64


def test_compute_call_provenance_input_sensitive():
    a = compute_call_provenance("X", "v1", {"targets": ["AHR"]}, {"delta": [0.1]}, [])
    b = compute_call_provenance("X", "v1", {"targets": ["TP53"]}, {"delta": [0.1]}, [])
    assert a["input_hash"] != b["input_hash"]


def test_check_call_provenance_complete_and_missing():
    ok = compute_call_provenance("X", "v1", {"a": 1}, {"b": 2}, [])
    assert check_call_provenance(ok) == []
    assert "model_version" in check_call_provenance({**ok, "model_version": None})
    assert "model_name" in check_call_provenance({})
    assert check_call_provenance("not_a_dict") == ["model_name", "model_version",
                                                   "input_hash", "output_hash"]


def test_per_call_hashes_in_report_for_used_models():
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    pch = sr["provenance"]["per_call_hashes"]
    assert sr["models_used"], "accept 请求应有 models_used"
    for name in sr["models_used"]:
        assert name in pch, f"{name} 缺 per_call_hashes"
        pc = pch[name]
        assert pc["model_name"] == name
        assert pc["model_version"]
        assert len(pc["input_hash"]) == 64 and len(pc["output_hash"]) == 64


def test_per_call_hash_offline_byte_equal_rerun():
    def _h(o): return hashlib.sha256(
        json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    outs = [run_query(dict(_ACCEPT), config=_CFG)["structured_report"] for _ in range(3)]
    assert len({_h(o) for o in outs}) == 1, "per_call hash 后 structured_report 三跑仍须字节等价"


class _BoomPredictor(PredictorAgent):
    """run_prediction 抛异常 → 走 handle 的 failed 分支。带 model_version 兜底。"""
    name = "BoomPredictor"
    model_version = "mock:BoomPredictor"

    def run_prediction(self, model_input: dict) -> dict:
        raise RuntimeError("boom")


def test_failed_branch_per_call_model_version_not_none():
    """failed 分支 per_call.model_version 走类属性兜底,须非 None(审查遗漏边界)。"""
    bus = MessageBus()
    bus.send(AgentMessage("b1", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    bc = {"species": "human", "species_supported": True,
          "model_applicability": {"BoomPredictor": {"supported_species": ["human"],
              "supported_modalities": ["scRNA"], "supported_tasks": ["predict_delta_expression"],
              "supported_perturbations": ["gene"]}}}
    req = {"species": "human", "input_modality": "scRNA",
           "task_type": "predict_delta_expression", "perturbation_type": "gene",
           "perturbation_targets": ["AHR"]}
    _BoomPredictor().handle(
        AgentMessage("m1", "X", "BoomPredictor", "predict",
                     {"request": req, "brain_context": bc}, "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "failed"
    pc = out["provenance"]["per_call"]
    assert pc["model_version"] == "mock:BoomPredictor", "failed 分支 model_version 须走兜底非 None"
    assert len(pc["input_hash"]) == 64 and len(pc["output_hash"]) == 64


def test_apply_gate_overrides_when_not_already_abstain():
    rep = {"abstain": False, "prediction": {"delta": [0.1]}, "provenance": {}}
    gated = apply_governance_gate(rep, "some_reason", "some_gate", {"detail": 1})
    assert gated is True
    assert rep["abstain"] is True and rep["prediction"] is None
    assert "some_reason" in rep["abstain_reasons"]
    g = rep["provenance"]["some_gate"]
    assert g["gate_abstained"] is True and g["reliability_original_abstain"] is False
    assert g["detail"] == 1


def test_apply_gate_records_but_no_override_when_already_abstain():
    rep = {"abstain": True, "prediction": None, "provenance": {}}
    gated = apply_governance_gate(rep, "r", "g", {})
    assert gated is False
    assert rep["provenance"]["g"]["gate_abstained"] is False
    assert rep["provenance"]["g"]["reliability_original_abstain"] is True


def test_gate_a_healthy_report_no_override():
    """正常 accept 请求 per_call 完整 → Gate A 不触发(无 provenance_hash_gate 或 gate_abstained=False)。"""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is False
    assert "provenance_hash_gate" not in sr["provenance"] or \
        sr["provenance"]["provenance_hash_gate"]["gate_abstained"] is False


def test_gate_a_triggers_on_incomplete_call_provenance(monkeypatch):
    """monkeypatch 使 per_call 缺 version → Gate A fail-closed abstain。"""
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev)
        pc["model_version"] = None
        return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is True
    assert "incomplete_call_provenance" in sr["abstain_reasons"]
    g = sr["provenance"]["provenance_hash_gate"]
    assert g["gate_abstained"] is True and g["missing"]


def test_check_report_provenance_complete():
    rep = {"models_used": [], "models_rejected": [], "reliability": "low",
           "provenance": {"n_messages": 3, "rules_referenced": [], "models_used": []}}
    assert check_report_provenance(rep) == []


def test_check_report_provenance_missing_top_and_prov_keys():
    rep = {"models_used": [], "provenance": {"n_messages": 3}}
    miss = check_report_provenance(rep)
    assert "models_rejected" in miss and "reliability" in miss
    assert "provenance.rules_referenced" in miss and "provenance.models_used" in miss


def test_check_report_provenance_provenance_not_dict():
    assert "provenance" in check_report_provenance({"models_used": [], "models_rejected": [],
                                                    "reliability": "low", "provenance": None})


def test_check_report_provenance_provenance_key_absent():
    rep = {"models_used": [], "models_rejected": [], "reliability": "low"}  # 无 provenance 键
    assert "provenance" in check_report_provenance(rep)


def test_gate_b_healthy_report_no_trigger():
    """活体验证:正常请求 provenance 契约完整 → Gate B 不触发(防御性 gate 罕触发的诚实证明)。"""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert "provenance_completeness_gate" not in sr["provenance"] or \
        sr["provenance"]["provenance_completeness_gate"]["gate_abstained"] is False
    assert sr["abstain"] is False


def test_gate_b_triggers_on_missing_provenance_key(monkeypatch):
    """monkeypatch check_report_provenance 返回非空 → Gate B fail-closed abstain(端到端接线验证)。"""
    monkeypatch.setattr("praxis_virtualcell.core.runtime.check_report_provenance",
                        lambda report: ["provenance.n_messages"])
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is True
    assert "incomplete_provenance" in sr["abstain_reasons"]
    g = sr["provenance"]["provenance_completeness_gate"]
    assert g["gate_abstained"] is True and g["missing"] == ["provenance.n_messages"]

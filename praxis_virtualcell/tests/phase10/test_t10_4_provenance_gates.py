"""P10.C2 provenance 完整性硬门 + per-call hash + 越界 cell type abstain 测试。
三 gate 全 C1 模式(runtime 后处理 override,不碰 reliability/critic 裁决数值)。"""
import hashlib
import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.governance.cell_type_domain import check_cell_type_domain
from praxis_virtualcell.governance.gate_util import apply_governance_gate
from praxis_virtualcell.governance.provenance_completeness import check_report_provenance
from praxis_virtualcell.governance.provenance_hash import check_call_provenance, compute_call_provenance
from praxis_virtualcell.predictors.base import PredictorAgent
from praxis_virtualcell.predictors.ml.agent_adapter import MLBackedPredictorAgent
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


_APPMAP = {"MockGEARS": {"supported_cell_types": ["K562", "A549"]},
           "MockCPA": {"supported_cell_types": ["K562"]},
           "NoDeclare": {}}


def test_cell_type_domain_all_out_of_domain():
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, ["MockGEARS", "MockCPA"]) == ["MockGEARS", "MockCPA"]


def test_cell_type_domain_in_domain_no_violation():
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({"cell_type": "K562"}, bc, ["MockGEARS", "MockCPA"]) == []


def test_cell_type_domain_partial_declare_only_declaring_checked():
    """有 predictor 无声明 supported_cell_types → 只对声明者判越界(窄门,同 reliability 语义):
    declaring=[MockGEARS],全越界 → 触发返回 [MockGEARS]。"""
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, ["MockGEARS", "NoDeclare"]) == ["MockGEARS"]


def test_cell_type_domain_partial_out_of_domain_no_trigger():
    """多声明 predictor 中仅部分越界 → 不触发(declaring=2, unsupported=1,非全越界)。"""
    bc = {"model_applicability": _APPMAP}
    # A549:MockGEARS 支持[K562,A549]、MockCPA 不支持[K562] → declaring=2、unsupported=1 → 不全越界
    assert check_cell_type_domain({"cell_type": "A549"}, bc, ["MockGEARS", "MockCPA"]) == []


def test_cell_type_domain_skips_when_reliability_abstained():
    """reliability 已 abstain(其它原因)→ Gate C 不独立触发(镜像 reliability not-abstain 守卫)。"""
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, ["MockGEARS"],
                                  reliability_abstained=True) == []


def test_cell_type_domain_no_cell_type_or_no_used():
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({}, bc, ["MockGEARS"]) == []                       # 无 cell_type
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, []) == []               # 无 used
    assert check_cell_type_domain({"cell_type": "HeLa"}, {}, ["MockGEARS"]) == []    # 无 appmap


def test_gate_c_out_of_domain_cell_type_abstains():
    """human gene 请求 + 越界 cell_type(Jurkat 全越界)→ Gate C 对外 abstain。"""
    req = dict(_ACCEPT)
    req["cell_type"] = "Jurkat"
    sr = run_query(req, config=_CFG)["structured_report"]
    assert sr["abstain"] is True
    assert "cell_type_out_of_domain" in sr["abstain_reasons"]
    g = sr["provenance"]["cell_type_gate"]
    assert g["gate_abstained"] is True and g["out_of_domain_predictors"]


def test_gate_c_in_domain_cell_type_no_trigger():
    """cell_type 在库(K562)→ Gate C 不触发。"""
    req = dict(_ACCEPT)
    req["cell_type"] = "K562"
    sr = run_query(req, config=_CFG)["structured_report"]
    assert sr["provenance"].get("cell_type_gate", {}).get("gate_abstained", False) is False


# ---- Task 5:收尾(多 gate 交互 + 裁决数值不变红线 + 确定性) ----

def test_c2_gate_preserves_reliability_numeric_fields(monkeypatch):
    """Gate 触发 abstain 后,reliability 提取字段(reliability/failed_checks/model_disagreement)
    与接线前一致 —— gate 只 override 对外,不改裁决数值(红线)。"""
    base = run_query(dict(_ACCEPT), config=_CFG)["structured_report"]
    base_fields = {k: base.get(k) for k in ("reliability", "failed_checks", "model_disagreement")}
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev)
        pc["input_hash"] = None
        return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    gated = run_query(dict(_ACCEPT), config=_CFG)["structured_report"]
    assert gated["abstain"] is True                         # Gate A 触发
    for k, v in base_fields.items():
        assert gated.get(k) == v, f"{k} 被 gate 改动(违红线):{v} -> {gated.get(k)}"


def test_multi_gate_reasons_accumulate_and_keys_independent(monkeypatch):
    """多 gate 同时命中:首个触发 gate override abstain,后续 gate no-op 但各记独立 provenance 键。
    实证(见 Task 5 报告):Gate A(缺 output_hash)先命中 → abstain_reasons=[incomplete_call_provenance]、
    provenance_hash_gate.gate_abstained=True;Gate C(cell_type 越界)后命中,report 已 abstain →
    no-op(不重复 append reason),但仍记 cell_type_gate 键且 gate_abstained=False、
    reliability_original_abstain=True(记录的是"进入 Gate C 前"的对外 abstain 态,即已被 Gate A
    override 后的状态,而非 reliability 原始判定——该请求 reliability 原判其实是 accept)。
    该场景未触发 Gate B(hash 断裂不影响 provenance 契约完整性),故 provenance_completeness_gate
    不出现,断言留容错分支。"""
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev)
        pc["output_hash"] = None
        return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    req = dict(_ACCEPT)
    req["cell_type"] = "Jurkat"                              # Gate A 缺 hash + Gate C 越界同时命中
    sr = run_query(req, config=_CFG)["structured_report"]
    assert sr["abstain"] is True
    assert sr["abstain_reasons"] == ["incomplete_call_provenance"]  # 仅 Gate A(首个命中),未重复 append
    assert "provenance_hash_gate" in sr["provenance"]              # Gate A provenance 键
    g_a = sr["provenance"]["provenance_hash_gate"]
    assert g_a["gate_abstained"] is True and g_a["reliability_original_abstain"] is False
    # Gate C 也命中但 report 已被 Gate A abstain → no-op(记 provenance 键,gate_abstained=False)
    assert "cell_type_gate" in sr["provenance"]
    g_c = sr["provenance"]["cell_type_gate"]
    assert g_c["gate_abstained"] is False
    # 进入 Gate C 前已被 Gate A override(非 reliability 原判)
    assert g_c["reliability_original_abstain"] is True
    assert g_c["out_of_domain_predictors"]
    # Gate B 该场景未触发(provenance 契约完整,只是 per_call hash 值为 None,不缺键)
    if "provenance_completeness_gate" in sr["provenance"]:
        assert sr["provenance"]["provenance_completeness_gate"]["gate_abstained"] is False


def test_c2_deterministic_no_llm():
    """OFFLINE 全程无 LLM 参与预测(C2 三 gate 均纯确定性函数)。
    llm_used_for_prediction 是 run_query() 顶层键(非 structured_report.provenance 内),
    与 test_t10_5_cross_module_consistency.py::test_c1_llm_never_used_for_prediction 断言口径一致。"""
    out = run_query(dict(_ACCEPT), config=_CFG)
    assert out["llm_used_for_prediction"] is False


def test_c2_gate_path_deterministic_rerun(monkeypatch):
    """Gate 触发路径(缺 hash)三跑 structured_report 字节等价(gate 确定性)。"""
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev)
        pc["input_hash"] = None
        return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    def _h(o):
        return hashlib.sha256(
            json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    outs = [run_query(dict(_ACCEPT), config=_CFG)["structured_report"] for _ in range(3)]
    assert len({_h(o) for o in outs}) == 1


class _FakeDonorModel:
    """Mac 无 torch 下构造 MLBackedPredictorAgent 用的最小桩(只需 eval())。"""

    def eval(self):
        return self


def test_ml_backed_predictor_declares_model_version():
    """C2 Gate A 兼容(opus final review 抓的跨 task 接缝):MLBackedPredictorAgent(远端真 ML 路径)
    须声明 model_version,否则 per_call.model_version=None → Gate A fail-closed 误伤对外 abstain。
    Mac 只验证 model_version 非 None(端到端不误伤需远端 .53 GPU,记 backlog)。"""
    agent = MLBackedPredictorAgent(_FakeDonorModel(), control=None, pert_table=None, pert_dim=0)
    assert agent.model_version                              # 非 None(消除 Gate A 误伤)
    assert agent.model_version.startswith("donor_ml")       # 诚实反映 donor 模型类型
    assert MLBackedPredictorAgent.model_version == "donor_ml"  # 类属性兜底非 None

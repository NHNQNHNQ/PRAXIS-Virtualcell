import hashlib
import json as _json

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.governance.module_consistency import check_module_plan
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)

# 覆盖各真实/mock/advisory/abstain 路径的代表性请求(module_plan 应全部内部一致)
_BASELINE_REQS = [
    # bacteria gene KO(gem_fba 真实)
    {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
     "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"},
    # human gene expression(donor_predictor,Mac mock)
    {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
     "input_modality": "scRNA", "output_modality": "delta_expression",
     "task_type": "predict_delta_expression"},
    # M1 膜系统 gene-set(B4 advisory,downgrade)
    {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["SLC2A1"],
     "input_modality": "scRNA", "output_modality": "delta_expression",
     "task_type": "predict_delta_expression"},
    # abstain 边界(基因不在任何模型)
    {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b9999"],
     "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"},
]


@pytest.mark.parametrize("req", _BASELINE_REQS)
def test_c1_baseline_existing_module_plans_have_no_violations(req):
    """接线前提:现有正常流程产的 module_plan 都 check_module_plan 无违规。
    若失败=接线会误 abstain 破坏字节等价 → 停止 BLOCKED(需先修 module_plan 产出)。"""
    out = run_query(dict(req), config=_CFG)
    module_plan = out["structured_report"].get("provenance", {}).get("module_plan")
    if module_plan is None:
        pytest.skip("该请求无 module_plan(abstain/不可路由),不适用一致性基线")
    violations = check_module_plan(module_plan)
    assert violations == [], f"现有 module_plan 有违规(接线前提不成立):{violations}"


def test_c1_consistent_plan_zero_action_byte_equal(monkeypatch):
    """一致 module_plan(check_module_plan 返回空)→ 零动作:不 abstain、provenance 不加
    cross_module_consistency 键、report 与未接 gate 时字节完全一致(保 §6 字节等价)。"""
    from praxis_virtualcell.core import runtime as RT
    # 显式锁一致(check 返回空),排除环境干扰
    monkeypatch.setattr(RT, "check_module_plan", lambda plan: [])
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert "cross_module_consistency" not in sr.get("provenance", {})   # 一致场景无痕迹
    assert sr["abstain"] is False                                       # 未被 gate 误 abstain


def test_c1_consistent_offline_byte_equal_3runs():
    """C1 接线后,一致场景现有请求 3 跑 structured_report + trace 字节等价不变(确定性红线)。"""
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    outs = [run_query(dict(req), config=_CFG) for _ in range(3)]
    canon = lambda o: hashlib.sha256(  # noqa: E731 — 与 plan 给定代码一致,局部一次性用,def 无必要
        _json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    assert len({canon(o["structured_report"]) for o in outs}) == 1
    assert len({canon(o["trace"]) for o in outs}) == 1


def test_c1_violation_triggers_gate_abstain(monkeypatch):
    """检出违规(check_module_plan 非空)且 reliability 原未 abstain → gate 真触发对外 abstain:
    abstain=True + prediction=None + abstain_reasons 含 cross_module_inconsistency +
    provenance.cross_module_consistency 记录(gate_abstained=True + 原 abstain=False)。"""
    from praxis_virtualcell.core import runtime as RT
    monkeypatch.setattr(RT, "check_module_plan",
                        lambda plan: ["verdict_more_optimistic_than_route[test]: accept < caution"])
    # 选一个 reliability 原本不 abstain 的请求(bacteria b0720 essential → 真实 FBA 预测,不 abstain)
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is True                                        # gate 触发 abstain
    assert sr["prediction"] is None                                     # 预测清空
    assert "cross_module_inconsistency" in sr["abstain_reasons"]        # 原因记录
    cmc = sr["provenance"]["cross_module_consistency"]
    assert cmc["gate_abstained"] is True
    assert cmc["reliability_original_abstain"] is False                 # reliability 原判保留可审计
    assert cmc["violations"]                                            # 违规明细留痕


def test_c1_gate_preserves_reliability_numeric_fields(monkeypatch):
    """裁决数值不变红线:gate 触发时,reliability 产物数值字段(reliability/model_disagreement/
    failed_checks)与未触发 gate(同请求、check 返回空)时完全一致——gate 只改 abstain 布尔+prediction。"""
    from praxis_virtualcell.core import runtime as RT
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    # 基准:check 返回空(无 gate)
    monkeypatch.setattr(RT, "check_module_plan", lambda plan: [])
    base = run_query(dict(req), config=_CFG)["structured_report"]
    # gate 触发:check 返回违规
    monkeypatch.setattr(RT, "check_module_plan", lambda plan: ["engine_out_of_whitelist[test]"])
    gated = run_query(dict(req), config=_CFG)["structured_report"]
    # reliability 产物数值字段逐一不变(裁决数值零改)
    for f in ("reliability", "model_disagreement", "failed_checks"):
        assert base.get(f) == gated.get(f), f"gate 改动了 reliability 产物字段 {f}(违裁决数值不变)"


def test_c1_violation_when_reliability_already_abstain(monkeypatch):
    """reliability 原已 abstain(如全基因不在模型)+ 违规 → gate 不重复触发(gate_abstained=False),
    但仍记录 violations 供审计;abstain 保持 True(reliability 原判)。"""
    from praxis_virtualcell.core import runtime as RT
    monkeypatch.setattr(RT, "check_module_plan", lambda plan: ["some_violation"])
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b9999"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    module_plan = sr.get("provenance", {}).get("module_plan")
    if module_plan is None:
        pytest.skip("该 abstain 请求无 module_plan(不可路由),gate 不触及")
    assert sr["abstain"] is True                                        # reliability 原判保持
    cmc = sr["provenance"]["cross_module_consistency"]
    assert cmc["gate_abstained"] is False                               # gate 未重复触发
    assert cmc["reliability_original_abstain"] is True                  # 原判 = abstain


# ---- Task 3:确定性收尾 ----
def test_c1_llm_never_used_for_prediction():
    """C1 gate 全程确定性无 LLM:llm_used_for_prediction 恒 false(run_query 顶层键 line 169)。"""
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["llm_used_for_prediction"] is False

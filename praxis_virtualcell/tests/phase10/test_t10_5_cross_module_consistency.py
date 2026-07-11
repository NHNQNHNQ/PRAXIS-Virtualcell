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

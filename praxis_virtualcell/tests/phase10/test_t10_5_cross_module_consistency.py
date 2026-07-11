import hashlib  # noqa: F401 — 供 Task 1+ 追加测试(字节等价 hash)复用,Task 0 阶段暂未使用
import json as _json  # noqa: F401 — 同上

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

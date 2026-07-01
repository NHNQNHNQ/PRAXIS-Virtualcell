"""W1.3(v0.4):case report 7 部分 validator + 3 个 routing-prototype case。

每个 v0.4 case 必须输出 7 部分(缺任一 → validate 失败):
  1 structured_input 2 object_normalization 3 models_tools_selected
  4 raw_output 5 baseline_comparison 6 reliability_decision 7 provenance_boundary

routing-prototype case(C3/C4/C5)的"分析输出"= 治理路由行为本身(真实、非 mock):
schema 归一 + route_table 路由,7 部分由真实 schema/routing 填充。C4/C5 的生长**数值**
预测留 W2 GEM 真跑,本步只验证"路由到正确引擎",boundary 里诚实标注。
"""
import pytest

from praxis_virtualcell.agents.case_report import (
    CaseReport, validate_case_report, routing_case, CaseReportError,
)

_FULL = dict(
    case_id="X", structured_input={"a": 1}, object_normalization={"b": 1},
    models_tools_selected={"c": 1}, raw_output={"d": 1}, baseline_comparison={"e": 1},
    reliability_decision={"f": 1}, provenance_boundary={"g": 1},
)


def test_validator_accepts_full_report():
    validate_case_report(CaseReport(**_FULL))          # 不抛


@pytest.mark.parametrize("missing", [
    "structured_input", "object_normalization", "models_tools_selected",
    "raw_output", "baseline_comparison", "reliability_decision", "provenance_boundary",
])
def test_validator_rejects_missing_or_empty(missing):
    bad = dict(_FULL)
    bad[missing] = {}                                  # 空 → 视为缺
    with pytest.raises(CaseReportError):
        validate_case_report(CaseReport(**bad))


def test_validator_accepts_dict_form():
    validate_case_report(dict(_FULL, case_id="Y"))     # dict 形式也可校验


# --- 3 个 routing-prototype case（方向正确 + 7 部分齐全）---

def test_case_C3_mouse_ortholog_routing():
    c = routing_case("C3_mouse_ortholog", {
        "species": "mouse", "cell_type": "fibroblast", "perturbation_object": "gene",
        "perturbation_targets": ["Trp53"], "target_output": "expression"})
    validate_case_report(c)
    d = c.to_dict()
    assert d["models_tools_selected"]["engine"] == "donor_predictor"
    assert d["reliability_decision"]["disposition"] in ("caution", "downgrade")
    assert any("ortholog" in x for x in d["reliability_decision"]["caution_flags"])


def test_case_C4_ecoli_ko_routes_gem():
    c = routing_case("C4_ecoli_ko_growth", {
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "gene",
        "perturbation_targets": ["b0720"], "target_output": "growth"})
    validate_case_report(c)
    d = c.to_dict()
    assert d["models_tools_selected"]["engine"] == "gem_fba"
    # 生长数值未跑 → boundary 必须诚实标注 pending
    assert "pending" in str(d["provenance_boundary"]).lower() or \
           "gem" in str(d["provenance_boundary"]).lower()


def test_case_C5_yeast_deletion_routes_gem():
    c = routing_case("C5_yeast_deletion_growth", {
        "species": "yeast", "cell_type": "S. cerevisiae", "perturbation_object": "gene",
        "perturbation_targets": ["YAL001C"], "target_output": "growth"})
    validate_case_report(c)
    assert c.to_dict()["models_tools_selected"]["engine"] == "gem_fba"

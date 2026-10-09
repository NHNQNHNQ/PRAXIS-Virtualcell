"""Phase 4:safety_contract —— LLM 只能从候选选的约束内核(纯函数,零 LLM)。
铁律(复刻 LLMRouter):越候选剔除、fail-closed(LLM 失败回退确定性 primary)、
不给 unsupported 硬解释(candidate 全集剔 unsupported)。"""
import json

from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.llm_orchestration import safety_contract as SC


def _req(**kw):
    base = {"species": "human", "perturbation_object": "gene",
            "target_output": "expression", "perturbation_targets": ["AHR"]}
    base.update(kw)
    return normalize_request(base)


def _support_all_strong():
    """8 模块全 strong(测 candidate 全集含非 unsupported)。"""
    return {mid: {"support": "strong", "verdict": "accept"} for mid in M.MODULE_ORDER}


def _support_with_unsupported():
    s = _support_all_strong()
    s["degradation_machinery"] = {"support": "unsupported", "verdict": "reject"}
    return s


def test_build_candidate_includes_deterministic_primary():
    cands = SC.build_candidate_modules(_req(), _support_all_strong())
    assert "genetic_hub" in cands             # human gene→expression 的确定性 primary
    assert set(cands) <= set(M.MODULE_ORDER)  # 全 ∈ 白名单
    assert cands == sorted(cands, key=M.MODULE_ORDER.index)  # 按 MODULE_ORDER 排序


def test_build_candidate_excludes_unsupported():
    """不给 unsupported module 硬解释:candidate 全集剔 unsupported。"""
    cands = SC.build_candidate_modules(_req(), _support_with_unsupported())
    assert "degradation_machinery" not in cands


def test_build_candidate_primary_survives_even_if_unsupported():
    """fail-closed:即使 support 把 primary 标 unsupported,primary 仍进候选(不丢主模块)。"""
    s = _support_all_strong()
    s["genetic_hub"] = {"support": "unsupported", "verdict": "reject"}
    cands = SC.build_candidate_modules(_req(), s)
    assert "genetic_hub" in cands             # primary 保底


def test_filter_to_supported_drops_out_of_candidate():
    cands = ["genetic_hub", "stress_processor"]
    out = SC.filter_to_supported_modules(
        ["genetic_hub", "not_a_module", "membrane_system"], cands)
    assert out == ["genetic_hub"]             # 越候选(含发明名)全剔


def test_filter_dedupes_and_preserves_candidate_order():
    cands = ["membrane_system", "genetic_hub", "stress_processor"]
    out = SC.filter_to_supported_modules(
        ["stress_processor", "genetic_hub", "genetic_hub"], cands)
    assert out == ["genetic_hub", "stress_processor"]   # 去重 + 按 candidates 序


def test_sanitize_valid_json_filters_selection():
    cands = ["genetic_hub", "stress_processor"]
    content = json.dumps({"selected_modules": ["genetic_hub", "membrane_system"],
                          "reasoning_summary": "x", "risk_flags": []})
    out = SC.sanitize_llm_plan(content, cands, primary="genetic_hub")
    assert out["selected_modules"] == ["genetic_hub"]   # membrane 越候选被剔
    assert out["reasoning_summary"] == "x"
    assert out["risk_flags"] == []


def test_sanitize_empty_content_is_fail_closed():
    cands = ["genetic_hub", "stress_processor"]
    out = SC.sanitize_llm_plan(None, cands, primary="genetic_hub")
    assert "llm_unavailable" in out["risk_flags"]
    assert "genetic_hub" in out["selected_modules"]     # 回退保底含 primary


def test_sanitize_bad_json_is_fail_closed():
    cands = ["genetic_hub"]
    out = SC.sanitize_llm_plan("not json{", cands, primary="genetic_hub")
    assert "llm_parse_failed" in out["risk_flags"]
    assert out["selected_modules"] == ["genetic_hub"]   # 回退保底


def test_sanitize_non_object_json_is_fail_closed():
    """漏洞 A:合法但非 object 的 JSON(list/int/null 等)→ d.get 会抛 AttributeError。
    必须 fail-closed:不崩溃、risk_flags 含 llm_parse_failed、selected 回退保底含 primary。"""
    cands = ["genetic_hub", "stress_processor"]
    for raw in ("[1,2,3]", "42", "null", "true", '"str"'):
        out = SC.sanitize_llm_plan(raw, cands, primary="genetic_hub")
        assert "llm_parse_failed" in out["risk_flags"], raw
        assert "genetic_hub" in out["selected_modules"], raw   # primary 保底


def test_sanitize_non_iterable_selected_is_fail_closed():
    """漏洞 B:selected_modules 为非可迭代标量(123)→ filter 内 set(123) 抛 TypeError。
    必须 fail-closed:不崩溃、回退保底含 primary。"""
    cands = ["genetic_hub", "stress_processor"]
    out = SC.sanitize_llm_plan('{"selected_modules": 123}', cands, primary="genetic_hub")
    assert "llm_parse_failed" in out["risk_flags"]
    assert "genetic_hub" in out["selected_modules"]            # primary 保底


def test_assert_plan_within_bounds_clean():
    plan = {"primary": "genetic_hub", "secondary": ["stress_processor"],
            "entries": [{"module": "genetic_hub"}, {"module": "stress_processor"}]}
    assert SC.assert_plan_within_bounds(plan, ["genetic_hub", "stress_processor"]) == []


def test_assert_plan_within_bounds_detects_out_of_candidate():
    plan = {"primary": "genetic_hub", "secondary": ["degradation_machinery"],
            "entries": [{"module": "genetic_hub"}, {"module": "degradation_machinery"}]}
    v = SC.assert_plan_within_bounds(plan, ["genetic_hub"])
    assert any("degradation_machinery" in x for x in v)

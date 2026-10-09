"""Tests for safety contract."""
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
    """Test helper: support all strong."""
    return {mid: {"support": "strong", "verdict": "accept"} for mid in M.MODULE_ORDER}


def _support_with_unsupported():
    s = _support_all_strong()
    s["degradation_machinery"] = {"support": "unsupported", "verdict": "reject"}
    return s


def test_build_candidate_includes_deterministic_primary():
    cands = SC.build_candidate_modules(_req(), _support_all_strong())
    assert "genetic_hub" in cands
    assert set(cands) <= set(M.MODULE_ORDER)
    assert cands == sorted(cands, key=M.MODULE_ORDER.index)


def test_build_candidate_excludes_unsupported():
    """Verify build candidate excludes unsupported."""
    cands = SC.build_candidate_modules(_req(), _support_with_unsupported())
    assert "degradation_machinery" not in cands


def test_build_candidate_primary_survives_even_if_unsupported():
    """Verify build candidate primary survives even if unsupported."""
    s = _support_all_strong()
    s["genetic_hub"] = {"support": "unsupported", "verdict": "reject"}
    cands = SC.build_candidate_modules(_req(), s)
    assert "genetic_hub" in cands


def test_filter_to_supported_drops_out_of_candidate():
    cands = ["genetic_hub", "stress_processor"]
    out = SC.filter_to_supported_modules(
        ["genetic_hub", "not_a_module", "membrane_system"], cands)
    assert out == ["genetic_hub"]


def test_filter_dedupes_and_preserves_candidate_order():
    cands = ["membrane_system", "genetic_hub", "stress_processor"]
    out = SC.filter_to_supported_modules(
        ["stress_processor", "genetic_hub", "genetic_hub"], cands)
    assert out == ["genetic_hub", "stress_processor"]


def test_sanitize_valid_json_filters_selection():
    cands = ["genetic_hub", "stress_processor"]
    content = json.dumps({"selected_modules": ["genetic_hub", "membrane_system"],
                          "reasoning_summary": "x", "risk_flags": []})
    out = SC.sanitize_llm_plan(content, cands, primary="genetic_hub")
    assert out["selected_modules"] == ["genetic_hub"]
    assert out["reasoning_summary"] == "x"
    assert out["risk_flags"] == []


def test_sanitize_empty_content_is_fail_closed():
    cands = ["genetic_hub", "stress_processor"]
    out = SC.sanitize_llm_plan(None, cands, primary="genetic_hub")
    assert "llm_unavailable" in out["risk_flags"]
    assert "genetic_hub" in out["selected_modules"]


def test_sanitize_bad_json_is_fail_closed():
    cands = ["genetic_hub"]
    out = SC.sanitize_llm_plan("not json{", cands, primary="genetic_hub")
    assert "llm_parse_failed" in out["risk_flags"]
    assert out["selected_modules"] == ["genetic_hub"]


def test_sanitize_non_object_json_is_fail_closed():
    """Verify sanitize non object json is fail closed."""
    cands = ["genetic_hub", "stress_processor"]
    for raw in ("[1,2,3]", "42", "null", "true", '"str"'):
        out = SC.sanitize_llm_plan(raw, cands, primary="genetic_hub")
        assert "llm_parse_failed" in out["risk_flags"], raw
        assert "genetic_hub" in out["selected_modules"], raw


def test_sanitize_non_iterable_selected_is_fail_closed():
    """Verify sanitize non iterable selected is fail closed."""
    cands = ["genetic_hub", "stress_processor"]
    out = SC.sanitize_llm_plan('{"selected_modules": 123}', cands, primary="genetic_hub")
    assert "llm_parse_failed" in out["risk_flags"]
    assert "genetic_hub" in out["selected_modules"]


def test_assert_plan_within_bounds_clean():
    plan = {"primary": "genetic_hub", "secondary": ["stress_processor"],
            "entries": [{"module": "genetic_hub"}, {"module": "stress_processor"}]}
    assert SC.assert_plan_within_bounds(plan, ["genetic_hub", "stress_processor"]) == []


def test_assert_plan_within_bounds_detects_out_of_candidate():
    plan = {"primary": "genetic_hub", "secondary": ["degradation_machinery"],
            "entries": [{"module": "genetic_hub"}, {"module": "degradation_machinery"}]}
    v = SC.assert_plan_within_bounds(plan, ["genetic_hub"])
    assert any("degradation_machinery" in x for x in v)

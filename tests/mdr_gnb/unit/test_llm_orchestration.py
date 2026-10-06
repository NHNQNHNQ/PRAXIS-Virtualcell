"""LLM 四模式编排(Phase 6,最后一相)。硬红线:OFFLINE 零 token 字节等价;
三 flag(modify_disposition/override_abstain/change_breakpoint)恒 False;LLM 产物只进 provenance notes。"""
import copy
import json

import pytest

from praxis_virtualcell.mdr_gnb.coordinator.llm_orchestration import (
    OrchestrationMode, enforce_boundaries, assert_orchestration_boundaries,
    build_candidate_outputs_for_drug, sanitize_llm_orchestration_plan,
    orchestrate_outputs, cross_species_review, detect_sir_mic_conflict,
    make_orchestration_client, run_query_with_mode, _BOUNDARY_FLAGS,
)


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


class _FakeClient:
    """duck-typed LLMClient:返回预设 content,记录调用次数(测零 token/越权)。"""
    def __init__(self, content, enabled=True):
        self._content = content
        self.enabled = enabled
        self.calls = 0

    def complete(self, messages, *, json_mode=False, max_tokens=1024):
        self.calls += 1
        return {"disabled": not self.enabled, "content": self._content, "error": None}


class _BoomClient:
    """OFFLINE 不该被调用:一旦 complete 被调用即炸(证明零 token)。"""
    enabled = True

    def complete(self, *a, **k):
        raise AssertionError("OFFLINE 路径不得调用 LLM(零 token 红线)")


def _raw(species="klebsiella_pneumoniae", drug="meropenem", drug_class="carbapenems",
         outputs=("SIR",)):
    return {"species": species,
            "drug_panel": [{"drug": drug, "drug_class": drug_class}],
            "requested_outputs": list(outputs),
            "amr_profile": {"blaKPC-2": True, "blaOXA-48": True, "blaNDM-1": True}}


# ---------- 模式枚举 ----------
def test_four_modes_exist():
    vals = {m.value for m in OrchestrationMode}
    assert vals == {"offline", "llm_parse_only", "llm_orchestrated_drugs", "llm_orchestrated_strict"}


# ---------- 三 flag 恒 False ----------
def test_enforce_boundaries_forces_false():
    p = enforce_boundaries({"modify_disposition": True, "override_abstain": True,
                            "change_breakpoint": True, "selected_outputs": ["sir_class"]})
    for f in _BOUNDARY_FLAGS:
        assert p[f] is False
    assert p["selected_outputs"] == ["sir_class"]     # 非 flag 字段保留


def test_assert_boundaries_raises_on_true():
    with pytest.raises(RuntimeError):
        assert_orchestration_boundaries({"modify_disposition": True})
    assert_orchestration_boundaries(enforce_boundaries({}))   # 全 False → 不抛


# ---------- 候选 output_kind ----------
def test_candidates_sir_default():
    cc = build_candidate_outputs_for_drug(requested_outputs=["SIR"])
    assert "sir_class" in cc["candidates"] and cc["primary"] == "sir_class"


def test_candidates_mic_weak_clips_to_sir():
    # 请求 MIC 但 mic 不支持 → 候选无 mic_scalar,primary 退 sir_class(MIC 弱→clip SIR)
    cc = build_candidate_outputs_for_drug(requested_outputs=["MIC"], mic_supported=False)
    assert "mic_scalar" not in cc["candidates"]
    assert cc["primary"] == "sir_class"


def test_candidates_failclosed_empty():
    cc = build_candidate_outputs_for_drug(requested_outputs=[], mic_supported=False)
    assert cc["candidates"] == ["sir_class"]


# ---------- sanitize(fail-closed + 三 flag) ----------
def test_sanitize_valid_subset():
    content = json.dumps({"selected_outputs": ["sir_class", "not_a_kind"],
                          "reasoning_summary": "ok", "risk_flags": ["x"]})
    p = sanitize_llm_orchestration_plan(content, ["sir_class", "mic_scalar"], primary="sir_class")
    assert p["selected_outputs"] == ["sir_class"]     # 越候选剔除
    for f in _BOUNDARY_FLAGS:
        assert p[f] is False


def test_sanitize_empty_fallback_primary():
    p = sanitize_llm_orchestration_plan(None, ["sir_class"], primary="sir_class")
    assert p["selected_outputs"] == ["sir_class"]
    assert "llm_unavailable" in p["risk_flags"]


def test_sanitize_garbage_failclosed():
    p = sanitize_llm_orchestration_plan("{not json", ["sir_class"], primary="sir_class")
    assert p["selected_outputs"] == ["sir_class"]
    assert "llm_parse_failed" in p["risk_flags"]


def test_sanitize_ignores_malicious_boundary_flags():
    # LLM 妄图 modify_disposition=True → 被硬钉 False(LLM 不裁决)
    content = json.dumps({"selected_outputs": ["sir_class"], "modify_disposition": True,
                          "override_abstain": True, "change_breakpoint": True})
    p = sanitize_llm_orchestration_plan(content, ["sir_class"], primary="sir_class")
    for f in _BOUNDARY_FLAGS:
        assert p[f] is False


def test_sanitize_primary_always_kept():
    content = json.dumps({"selected_outputs": []})   # LLM 删空
    p = sanitize_llm_orchestration_plan(content, ["sir_class", "mic_scalar"], primary="sir_class")
    assert "sir_class" in p["selected_outputs"]       # primary 保底


# ---------- orchestrate_outputs ----------
def test_orchestrate_disabled_client_fallback():
    plan = orchestrate_outputs({"requested_outputs": ["SIR"], "mic_supported": True}, client=None)
    assert "sir_class" in plan["selected_outputs"]
    for f in _BOUNDARY_FLAGS:
        assert plan[f] is False


def test_orchestrate_with_client_stays_in_candidates():
    fc = _FakeClient(json.dumps({"selected_outputs": ["sir_class", "synergy"]}))
    plan = orchestrate_outputs({"requested_outputs": ["SIR"], "mic_supported": True}, client=fc)
    assert set(plan["selected_outputs"]) <= set(plan["candidates"])
    assert fc.calls == 1


# ---------- 跨物种/SIR-MIC 冲突(确定性,advisory) ----------
def test_detect_conflict_deterministic():
    assert detect_sir_mic_conflict("R", "S") is True
    assert detect_sir_mic_conflict("R", "R") is False
    assert detect_sir_mic_conflict("R", None) is False


def test_cross_species_review_flags_conflict_no_verdict_change():
    pairs = [{"species": "klebsiella_pneumoniae", "drug": "meropenem", "sir": "R", "mic_call": "S"}]
    out = cross_species_review(pairs, client=None)
    assert out["conflicts"]                          # 确定性检出冲突
    for f in _BOUNDARY_FLAGS:
        assert out[f] is False                       # advisory 不裁决


# ---------- client 工厂:OFFLINE 零 token ----------
def test_make_client_offline_disabled():
    assert make_orchestration_client(OrchestrationMode.OFFLINE, api_key="k").enabled is False
    assert make_orchestration_client(OrchestrationMode.LLM_ORCHESTRATED_DRUGS, api_key="").enabled is False
    assert make_orchestration_client(OrchestrationMode.LLM_ORCHESTRATED_DRUGS, api_key="k").enabled is True


# ---------- 四模式 harness:OFFLINE 字节等价 + 零 token ----------
def test_offline_zero_token_never_calls_llm():
    # OFFLINE 传入会炸的 client,harness 绝不调用它(零 token 红线)
    r = run_query_with_mode(_raw(), mode=OrchestrationMode.OFFLINE, seed_task_id="t", client=_BoomClient())
    assert "report" in r


def test_offline_byte_identical():
    r1 = run_query_with_mode(_raw(), mode=OrchestrationMode.OFFLINE, seed_task_id="t")
    r2 = run_query_with_mode(_raw(), mode=OrchestrationMode.OFFLINE, seed_task_id="t")
    assert r1["trace"] == r2["trace"]
    assert r1["report"] == r2["report"]


def test_orchestrated_decision_equals_offline():
    # 红线:orchestrated 模式(无 key/disabled)裁决字段 == OFFLINE,只多 provenance.llm_* 键
    off = run_query_with_mode(_raw(), mode=OrchestrationMode.OFFLINE, seed_task_id="t")
    orch = run_query_with_mode(_raw(), mode=OrchestrationMode.LLM_ORCHESTRATED_DRUGS,
                               seed_task_id="t", client=None)
    for k in ("sir", "sir_prob", "abstained", "abstain_reasons", "downgrade_reasons",
              "caution_flags", "critic_violations", "drug", "task_id", "output_kind"):
        assert orch["report"][k] == off["report"][k], f"裁决字段 {k} 被 LLM 改动"
    assert orch["report"]["provenance"]["route"] == off["report"]["provenance"]["route"]
    assert "llm_orchestration" in orch["report"]["provenance"]


def test_strict_mode_malicious_client_cannot_change_verdict():
    # STRICT + 恶意 client(妄改裁决)→ 裁决不变,三 flag 恒 False
    off = run_query_with_mode(_raw(), mode=OrchestrationMode.OFFLINE, seed_task_id="t")
    evil = _FakeClient(json.dumps({"selected_outputs": ["mic_scalar"], "modify_disposition": True,
                                   "override_abstain": True, "notes": ["x"], "flags": ["y"]}))
    strict = run_query_with_mode(_raw(), mode=OrchestrationMode.LLM_ORCHESTRATED_STRICT,
                                 seed_task_id="t", client=evil)
    assert strict["report"]["sir"] == off["report"]["sir"]
    assert strict["report"]["abstained"] == off["report"]["abstained"]
    orch = strict["report"]["provenance"]["llm_orchestration"]
    for f in _BOUNDARY_FLAGS:
        assert orch[f] is False
    assert "llm_cross_species" in strict["report"]["provenance"]


def test_harness_does_not_mutate_input_report():
    # harness 返回新 report,原 run_mdr_query 结果不被 mutate
    off = run_query_with_mode(_raw(), mode=OrchestrationMode.OFFLINE, seed_task_id="t")
    snap = copy.deepcopy(off["report"])
    run_query_with_mode(_raw(), mode=OrchestrationMode.LLM_ORCHESTRATED_STRICT,
                        seed_task_id="t", client=None)
    assert off["report"] == snap

"""E0-E5 证据等级薄层:只读挂 provenance,不动裁决,永不 promote(Phase 4)。"""
import copy

from praxis_virtualcell.mdr_gnb.coordinator.evidence_level import attach_evidence_level


def _report(abstained=False, sir="R", abstain_reasons=None, downgrade_reasons=None,
            caution_flags=None, provenance=None):
    return {
        "task_id": "t", "drug": "meropenem", "abstained": abstained,
        "sir": sir, "sir_prob": {"S": 0.34, "I": 0.0, "R": 0.66},
        "abstain_reasons": abstain_reasons or [], "downgrade_reasons": downgrade_reasons or [],
        "caution_flags": caution_flags or [], "critic_violations": [],
        "provenance": provenance or {"route": "accept"},
    }


def test_abstain_maps_e0_e1():
    # 硬拒 abstain → E0
    r = attach_evidence_level(_report(abstained=True, abstain_reasons=["core_predictor_failed"]))
    assert r["provenance"]["evidence_level"]["level"] == "E0"
    # 软 abstain → E1
    r2 = attach_evidence_level(_report(abstained=True, abstain_reasons=["insufficient_mic_samples"]))
    assert r2["provenance"]["evidence_level"]["level"] == "E1"


def test_accept_maps_e2_e3():
    r = attach_evidence_level(_report(abstained=False))
    lvl = r["provenance"]["evidence_level"]["level"]
    assert lvl in ("E2", "E3")   # accept 级(runtime OOD unknown → 多为 E3)


def test_downgrade_maps_e4():
    r = attach_evidence_level(_report(abstained=False, downgrade_reasons=["mic_requested_but_only_rule_fallback"]))
    assert r["provenance"]["evidence_level"]["level"] == "E4"


def test_combo_gate_status_in_rationale_and_conservative():
    # combo_gate degrade → 更保守(E4),不 promote
    r = attach_evidence_level(_report(abstained=False), combo_gate_status="degrade_classification")
    ev = r["provenance"]["evidence_level"]
    assert ev["level"] == "E4"
    assert any("combo_gate" in x for x in ev["rationale"])


def test_never_promote_abstain_to_accept():
    # abstain 永不被 combo_gate=pass 抬成 accept 级(E2/E3)
    r = attach_evidence_level(_report(abstained=True, abstain_reasons=["species_uncertain"]),
                              combo_gate_status="pass")
    assert r["provenance"]["evidence_level"]["level"] in ("E0", "E1")   # 仍 abstain 侧


def test_byte_identical_decision_fields():
    # 红线:evidence_level 挂载前后 prediction/verdict/abstain 完全不变
    orig = _report(abstained=False, sir="R")
    snapshot = copy.deepcopy(orig)
    out = attach_evidence_level(orig)
    # 原 report 未被 mutate
    assert orig == snapshot
    # 输出的裁决字段与原一致(只多 provenance.evidence_level)
    for k in ("sir", "sir_prob", "abstained", "critic_violations", "abstain_reasons",
              "downgrade_reasons", "drug", "task_id"):
        assert out[k] == orig[k]
    assert "evidence_level" in out["provenance"]
    assert out["provenance"]["route"] == orig["provenance"]["route"]


def test_aligned_with_disposition_flag():
    r = attach_evidence_level(_report(abstained=True, abstain_reasons=["species_uncertain"]))
    assert r["provenance"]["evidence_level"]["aligned_with_disposition"] is True

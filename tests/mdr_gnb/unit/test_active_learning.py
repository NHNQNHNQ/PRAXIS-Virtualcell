"""主动学习 advisory:AMR 场景「该测什么」优先队列(Phase 5)。
红线:只加 provenance.active_learning,不碰 prediction/verdict/reliability(byte-identical)。"""
import copy

from praxis_virtualcell.mdr_gnb.coordinator.active_learning import (
    attach_active_learning, build_amr_learning_queue,
)


def _report(abstained=False, sir="R", downgrade_reasons=None, caution_flags=None,
            drug="meropenem", provenance=None):
    return {
        "task_id": "t", "drug": drug, "abstained": abstained,
        "sir": None if abstained else sir,
        "sir_prob": None if abstained else {"S": 0.34, "I": 0.0, "R": 0.66},
        "output_kind": "sir_class",
        "abstain_reasons": ["core_predictor_failed"] if abstained else [],
        "downgrade_reasons": downgrade_reasons or [], "caution_flags": caution_flags or [],
        "critic_violations": [], "provenance": provenance or {"route": "accept"},
    }


def _req(species="klebsiella_pneumoniae", drug="meropenem", drug_class="carbapenems",
         amr_profile=None, assay_context=None, outputs=("SIR",)):
    return {"species": species, "drug": drug, "drug_class": drug_class,
            "amr_profile": amr_profile or {"blaKPC-2": True},
            "assay_context": assay_context or {},
            "requested_outputs": list(outputs)}


def _ev(level):
    return {"level": level, "rationale": []}


def _items(report):
    return report["provenance"]["active_learning"]["items"]


def test_abstain_must_produce_next_experiment():
    r = attach_active_learning(_report(abstained=True), evidence_level=_ev("E0"), request=_req())
    its = _items(r)
    assert its, "abstain 必产候选"
    assert any(it["experiment_type"] == "next_experiment" for it in its)


def test_downgrade_must_produce_next_experiment():
    r = attach_active_learning(
        _report(downgrade_reasons=["mic_requested_but_only_rule_fallback"]),
        evidence_level=_ev("E4"), request=_req())
    its = _items(r)
    assert any(it["experiment_type"] == "next_experiment" for it in its)


def test_caution_must_produce_next_experiment():
    r = attach_active_learning(
        _report(caution_flags=["non_reference_strain"]),
        evidence_level=_ev("E3"), request=_req())
    assert any(it["experiment_type"] == "next_experiment" for it in _items(r))


def test_accept_produces_refinement():
    # E2/E3 accept(无 abstain/downgrade/caution)→ refinement
    r = attach_active_learning(_report(abstained=False), evidence_level=_ev("E3"), request=_req())
    its = _items(r)
    assert its
    assert any(it["experiment_type"] == "refinement" for it in its)


def test_rejected_drug_class_gives_test_drug_class():
    # 被拒 drug_class(abstain)→ test_drug_class action
    r = attach_active_learning(_report(abstained=True), evidence_level=_ev("E0"),
                               request=_req(drug_class="polymyxins"))
    assert any(it["action"] == "test_drug_class" for it in _items(r))


def test_weak_assay_gives_switch_assay():
    r = attach_active_learning(
        _report(downgrade_reasons=["mic_requested_but_only_rule_fallback"]),
        evidence_level=_ev("E4"), request=_req())
    assert any(it["action"] == "switch_assay" for it in _items(r))


def test_weak_species_gives_bootstrap_isolates():
    # stenotrophomonas_maltophilia 无 SIR 模型 → bootstrap_isolates
    r = attach_active_learning(
        _report(abstained=False), evidence_level=_ev("E3"),
        request=_req(species="stenotrophomonas_maltophilia", drug="levofloxacin",
                     drug_class="fluoroquinolones"))
    assert any(it["action"] == "bootstrap_isolates" for it in _items(r))


def test_items_have_expected_information_gain():
    r = attach_active_learning(_report(abstained=True), evidence_level=_ev("E5"), request=_req())
    for it in _items(r):
        assert isinstance(it["expected_information_gain"], (int, float))


def test_queue_sorted_desc_by_gain():
    r = attach_active_learning(
        _report(downgrade_reasons=["mic_requested_but_only_rule_fallback"]),
        evidence_level=_ev("E4"),
        request=_req(species="stenotrophomonas_maltophilia"))
    gains = [it["expected_information_gain"] for it in _items(r)]
    assert gains == sorted(gains, reverse=True)


def test_advisory_never_touches_decision_fields():
    # 红线:attach 前后裁决字段一字不变,原 report 不 mutate,只多 provenance.active_learning
    orig = _report(abstained=False, sir="R")
    snap = copy.deepcopy(orig)
    out = attach_active_learning(orig, evidence_level=_ev("E3"), request=_req())
    assert orig == snap                                  # 入参未被 mutate
    for k in ("sir", "sir_prob", "abstained", "critic_violations",
              "abstain_reasons", "downgrade_reasons", "caution_flags", "drug", "task_id"):
        assert out[k] == orig[k]
    assert "active_learning" in out["provenance"]
    assert out["provenance"]["route"] == orig["provenance"]["route"]


def test_no_request_still_safe():
    # 无 request/module_plan → 仍产队列不崩(用 report 内信息)
    q = build_amr_learning_queue(_report(abstained=True), evidence_level=_ev("E1"))
    assert "items" in q.to_dict()

"""report_builder:分离 abstain(隐藏预测)/downgrade(保留),固定免责声明,critic 违规透出。"""
from praxis_virtualcell.mdr_gnb.coordinator.report_builder import build_report

_DISCLAIMER = "仅供科研筛选,不构成临床用药决策"


def test_abstain_report_hides_prediction():
    rep = build_report(
        task_id="t1", drug="meropenem",
        ensemble_result={"output_kind": "mic_scalar", "ensemble": {"mic_scalar": 2.0}},
        abstain=True, abstain_reasons=["insufficient_mic_samples"],
        downgrade_reasons=[], caution_flags=[], breakpoint_source="EUCAST v14.0",
        critic_violations=[], provenance={"src": "x"})
    assert rep["abstained"] is True
    assert rep["mic_range"] is None and rep["sir"] is None
    assert rep["abstain_reasons"] == ["insufficient_mic_samples"]
    assert _DISCLAIMER in rep["disclaimer"]


def test_downgrade_keeps_prediction_separate_reasons():
    rep = build_report(
        task_id="t2", drug="ciprofloxacin",
        ensemble_result={"output_kind": "sir_class",
                         "ensemble": {"sir": "R", "sir_prob": {"S": 0.1, "I": 0.1, "R": 0.8}}},
        abstain=False, abstain_reasons=[],
        downgrade_reasons=["mic_requested_but_only_rule_fallback"],
        caution_flags=["intrinsic_resistance_species"],
        breakpoint_source="EUCAST v14.0", critic_violations=[], provenance={"src": "rule"})
    assert rep["abstained"] is False
    assert rep["sir"] == "R"
    assert rep["abstain_reasons"] == []
    assert rep["downgrade_reasons"] == ["mic_requested_but_only_rule_fallback"]
    assert "intrinsic_resistance_species" in rep["caution_flags"]


def test_critic_violations_surface():
    rep = build_report(
        task_id="t3", drug="meropenem",
        ensemble_result={"output_kind": "mic_scalar", "ensemble": {"mic_scalar": 16.0}},
        abstain=False, abstain_reasons=[], downgrade_reasons=[], caution_flags=[],
        breakpoint_source="EUCAST v14.0",
        critic_violations=["mechanism_claim_without_g3"], provenance={"src": "x"})
    assert rep["critic_violations"] == ["mechanism_claim_without_g3"]

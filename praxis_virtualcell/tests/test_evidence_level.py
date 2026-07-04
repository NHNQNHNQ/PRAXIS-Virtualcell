"""Phase 5:evidence_level —— E0–E5 映射(纯函数,零 LLM)。
决策 B:治理层之上的薄映射,不重写治理、不回写 verdict;E2/E3 accept 级只在现有 disposition
已 accept 时给出(不领先治理);OOD 未知 fail-closed 记 unknown(红线 6)。"""
from praxis_virtualcell.governance import evidence_level as EL


def _report(**kw):
    base = {"abstain": False, "reliability": "high", "prediction": {"delta": [0.3]},
            "models_used": ["MockLinear", "MockCPA"], "abstain_reasons": [],
            "downgrade_reasons": [], "model_disagreement": {"score": 0.2, "triggered": False},
            "caution_flags": {}, "learned_reliability": None,
            "request": {"species": "human"}, "seen_in_train": True,
            "provenance": {}}
    base.update(kw)
    return base


def test_ood_signal_in_domain():
    assert EL.derive_ood_signal(_report(seen_in_train=True)) == "in_domain"


def test_ood_signal_ood():
    assert EL.derive_ood_signal(_report(seen_in_train=False)) == "ood"


def test_ood_signal_unknown_when_none_and_human_no_caution():
    # seen_in_train=None + human + 无 caution → 仍 unknown(runtime seen_in_train 多 None,不假装 in_domain)
    assert EL.derive_ood_signal(_report(seen_in_train=None)) == "unknown"


def test_ood_signal_unknown_when_cross_species():
    r = _report(seen_in_train=None, request={"species": "mouse"})
    assert EL.derive_ood_signal(r) == "unknown"


def test_e2_in_domain_accept():
    """E2:非 abstain、无 downgrade、high、in_domain、disagreement 未触发 → E2(与 disposition accept 对齐)。"""
    out = EL.map_evidence_level(_report(seen_in_train=True))
    assert out["level"] == "E2"
    assert out["ood_signal"] == "in_domain"
    assert out["aligned_with_disposition"] is True


def test_e3_accept_with_caution_or_unknown_ood():
    """E3:accept 但 OOD 未知/有 caution/非母种。"""
    out = EL.map_evidence_level(_report(seen_in_train=None, reliability="high"))
    assert out["level"] == "E3"


def test_e4_downgrade():
    out = EL.map_evidence_level(_report(reliability="medium",
                                        downgrade_reasons=["downgrade:model_disagreement_too_high"]))
    assert out["level"] == "E4"


def test_e5_disagreement_triggered_not_abstain():
    out = EL.map_evidence_level(_report(reliability="low",
                                        model_disagreement={"score": 0.9, "triggered": True}))
    assert out["level"] == "E5"


def test_e5_learned_fallback():
    out = EL.map_evidence_level(_report(reliability="low",
                                        learned_reliability={"fallback": True}))
    assert out["level"] == "E5"


def test_e1_abstain():
    out = EL.map_evidence_level(_report(abstain=True, prediction=None, models_used=[],
                                        abstain_reasons=["model_disagreement_too_high"]))
    assert out["level"] == "E1"


def test_e0_hard_reject():
    out = EL.map_evidence_level(_report(abstain=True, prediction=None, models_used=[],
                                        abstain_reasons=["species_not_supported"]))
    assert out["level"] == "E0"


def test_e_level_does_not_lead_disposition():
    """红线/决策 B:downgrade 请求不得被映射成 E2/E3 accept 级。"""
    out = EL.map_evidence_level(_report(seen_in_train=True, reliability="high",
                                        downgrade_reasons=["downgrade:cell_type_not_supported"]))
    assert out["level"] in ("E4", "E5")   # 有 downgrade → 不得 E2/E3
    assert out["aligned_with_disposition"] is True


def test_map_does_not_mutate_report():
    """不回写:map 只读不改 report。"""
    r = _report()
    snap = dict(r)
    EL.map_evidence_level(r)
    assert r == snap

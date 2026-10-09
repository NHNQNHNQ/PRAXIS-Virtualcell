"""Tests for acquisition."""
from praxis_virtualcell.active_learning import acquisition as AQ


def test_high_disagreement_higher_gain():
    lo = AQ.information_gain({"disagreement_score": 0.1, "disagreement_triggered": False,
                              "ood_signal": "in_domain", "evidence_level": "E2",
                              "module_weak": False})
    hi = AQ.information_gain({"disagreement_score": 0.9, "disagreement_triggered": True,
                              "ood_signal": "in_domain", "evidence_level": "E2",
                              "module_weak": False})
    assert hi > lo


def test_ood_higher_than_in_domain():
    ind = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": False})
    ood = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "ood", "evidence_level": "E2", "module_weak": False})
    assert ood > ind


def test_unknown_ood_between_or_above_in_domain():
    ind = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": False})
    unk = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "unknown", "evidence_level": "E2", "module_weak": False})
    assert unk > ind


def test_worse_evidence_higher_gain():
    e2 = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                             "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": False})
    e5 = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                             "ood_signal": "in_domain", "evidence_level": "E5", "module_weak": False})
    assert e5 > e2


def test_module_weak_adds_gain():
    strong = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                                 "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": False})
    weak = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": True})
    assert weak > strong


def test_deterministic_reproducible():
    s = {"disagreement_score": 0.5, "disagreement_triggered": True, "ood_signal": "ood",
         "evidence_level": "E4", "module_weak": True}
    assert AQ.information_gain(s) == AQ.information_gain(s)


def test_missing_signals_fail_safe_zero_base():

    g = AQ.information_gain({})
    assert isinstance(g, float)
    assert g == g

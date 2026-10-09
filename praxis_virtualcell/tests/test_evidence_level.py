"""Tests for evidence level."""
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

    assert EL.derive_ood_signal(_report(seen_in_train=None)) == "unknown"


def test_ood_signal_unknown_when_cross_species():
    r = _report(seen_in_train=None, request={"species": "mouse"})
    assert EL.derive_ood_signal(r) == "unknown"


def test_e2_in_domain_accept():
    """Verify e2 in domain accept."""
    out = EL.map_evidence_level(_report(seen_in_train=True))
    assert out["level"] == "E2"
    assert out["ood_signal"] == "in_domain"
    assert out["aligned_with_disposition"] is True


def test_e3_accept_with_caution_or_unknown_ood():
    """Verify e3 accept with caution or unknown ood."""
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


def test_e0_core_predictor_failed():
    """Verify e0 core predictor failed."""
    out = EL.map_evidence_level(_report(abstain=True, prediction=None, models_used=[],
                                        abstain_reasons=["core_predictor_failed"]))
    assert out["level"] == "E0"


def test_e_level_does_not_lead_disposition():
    """Verify e level does not lead disposition."""
    out = EL.map_evidence_level(_report(seen_in_train=True, reliability="high",
                                        downgrade_reasons=["downgrade:cell_type_not_supported"]))
    assert out["level"] in ("E4", "E5")
    assert out["aligned_with_disposition"] is True


def test_map_does_not_mutate_report():
    """Verify map does not mutate report."""
    r = _report()
    snap = dict(r)
    EL.map_evidence_level(r)
    assert r == snap

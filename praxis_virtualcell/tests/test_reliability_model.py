"""Tests for reliability model."""
from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import reliability_model as rm

LEDGER = "docs/findings/m1_ledger_151.jsonl"


def test_learned_beats_single_signal_baselines():
    led = EvalLedger.from_jsonl(LEDGER)
    res = rm.evaluate(led.entries, k=5)
    a = res["auroc"]
    assert res["n"] >= 100
    assert res["reg_corr_pred_vs_true"] > 0.5
    assert a["learned"] > a["disagreement_only"]
    assert a["learned"] > a["ood_only"]
    assert a["disagreement_only"] > a["random"] + 0.1
    assert a["learned"] > 0.8


def test_no_leakage_features_only():

    from praxis_virtualcell.governance import ledger_features as lf
    assert not (set(rm.FEATURES) & set(lf.LABELS))

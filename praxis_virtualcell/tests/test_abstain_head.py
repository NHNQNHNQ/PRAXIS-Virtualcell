"""Tests for abstain head."""
from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import abstain_head as ah

LEDGER = "docs/findings/m1_ledger_151.jsonl"


def test_learned_abstain_beats_disagreement_rule():
    led = EvalLedger.from_jsonl(LEDGER)
    res = ah.evaluate_abstain(led.entries, k=5)
    auc = {k: v["auc"] for k, v in res.items()}
    assert auc["oracle"] > auc["learned"]
    assert auc["learned"] > auc["disagreement_only"]
    assert auc["disagreement_only"] > auc["random"]

    cur = dict(res["learned"]["curve"])
    assert cur[0.6] > cur[1.0]


def test_risk_coverage_curve_shape():
    led = EvalLedger.from_jsonl(LEDGER)
    res = ah.evaluate_abstain(led.entries, k=5)

    full = {k: dict(v["curve"])[1.0] for k, v in res.items()}
    assert max(full.values()) - min(full.values()) < 1e-6

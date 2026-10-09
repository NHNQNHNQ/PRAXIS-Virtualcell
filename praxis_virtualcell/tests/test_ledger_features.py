"""Tests for ledger features."""
from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import ledger_features as lf

LEDGER = "docs/findings/m1_ledger_sample.jsonl"


def test_no_label_leak_in_features():

    assert not (set(lf.INFERENCE_FEATURES) & set(lf.LABELS))
    led = EvalLedger.from_jsonl(LEDGER)
    rows = lf.extract_features(led.entries)
    assert len(rows) == len(led.entries)

    for r in rows:
        assert set(r.keys()) == set(lf.INFERENCE_FEATURES)
        assert "delta_pearson" not in r and "per_predictor_delta_pearson" not in r


def test_labels_available_separately():
    led = EvalLedger.from_jsonl(LEDGER)
    e = led.entries[0]
    assert lf.reliability_target(e) is not None
    assert lf.router_label(e) in ("MockLinear", "MockCPA", "MockGEARS")


def test_perturbation_level_folds_disjoint_and_complete():
    led = EvalLedger.from_jsonl(LEDGER)
    folds = lf.leave_perturbation_out_folds(led.entries, k=5)
    assert len(folds) == 5
    n = len(led.entries)
    for train, test in folds:
        assert set(train) & set(test) == set()
        assert set(train) | set(test) == set(range(n))

    seen = sorted(i for _, test in folds for i in test)
    assert seen == list(range(n))

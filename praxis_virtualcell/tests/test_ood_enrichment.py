"""Tests for ood enrichment."""
import math

from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import ood_enrichment as oe

LEDGER = "docs/findings/m1_ledger_151.jsonl"


def _entries():
    return EvalLedger.from_jsonl(LEDGER).entries


def test_ood_labels_mapping():
    """Verify ood labels mapping."""
    labs = oe.ood_labels([{"seen_in_train": True}, {"seen_in_train": False}, {"seen_in_train": None}])
    assert labs == [False, True, None]


def test_base_rate_matches_split():
    """Verify base rate matches split."""
    res = oe.evaluate_ood(_entries())
    assert res["n_ood"] == 82
    assert res["n_seen"] == 69
    assert 0.53 <= res["base_rate_ood"] <= 0.55


def test_learned_abstain_enriches_ood():
    """Verify learned abstain enriches ood."""
    res = oe.evaluate_ood(_entries())
    assert res["learned_flagged_ood_frac"] > res["base_rate_ood"]
    assert res["odds_ratio_learned"] > 1.0


def test_subset_risk_coverage_finite():
    """Verify subset risk coverage finite."""
    res = oe.evaluate_ood(_entries())
    for key in ("rc_auc_ood_only", "rc_auc_seen_only"):
        v = res[key]
        assert isinstance(v, float) and not math.isnan(v) and math.isfinite(v)

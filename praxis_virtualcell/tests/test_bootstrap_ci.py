"""Tests for bootstrap ci."""
from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import bootstrap_ci as bc

LEDGER = "docs/findings/m1_ledger_151.jsonl"


def _entries():
    return EvalLedger.from_jsonl(LEDGER).entries


def test_point_estimates_reproduce_known_findings():
    """Verify point estimates reproduce known findings."""
    res = bc.run(_entries(), b=200, seed=0)
    m = res["metrics"]
    assert res["n"] >= 150

    assert 0.88 <= m["auroc_learned"]["point"] <= 0.93
    assert 0.74 <= m["auroc_disagreement"]["point"] <= 0.80

    assert 0.72 <= m["rc_auc_learned"]["point"] <= 0.77
    assert 0.70 <= m["rc_auc_disagreement"]["point"] <= 0.74

    assert m["mc_wrong_accept_rule"]["point"] > 0.9          # 0.974
    assert 0.15 <= m["mc_wrong_accept_learned"]["point"] <= 0.27   # 0.211
    assert m["mc_risk_coverage_rule"]["point"] < 0.10        # 0.026
    assert m["mc_risk_coverage_learned"]["point"] > 0.70     # 0.789


def test_ci_brackets_point_and_ordered():
    """Verify ci brackets point and ordered."""
    res = bc.run(_entries(), b=300, seed=0)
    for name, d in res["metrics"].items():
        assert d["ci_lo"] <= d["ci_hi"], name
        assert d["ci_lo"] <= d["point"] <= d["ci_hi"], name
        assert d["ci_lo"] <= d["median"] <= d["ci_hi"], name


def test_deterministic_under_fixed_seed():
    """Verify deterministic under fixed seed."""
    a = bc.run(_entries(), b=200, seed=0)
    b = bc.run(_entries(), b=200, seed=0)
    assert a["metrics"]["auroc_learned"]["ci_lo"] == b["metrics"]["auroc_learned"]["ci_lo"]
    assert a["metrics"]["auroc_learned"]["ci_hi"] == b["metrics"]["auroc_learned"]["ci_hi"]
    assert a["metrics"]["mc_wrong_accept_learned"]["ci_lo"] == b["metrics"]["mc_wrong_accept_learned"]["ci_lo"]


def test_learned_minus_disagreement_diff_present_and_directional():
    """Verify learned minus disagreement diff present and directional."""
    res = bc.run(_entries(), b=300, seed=0)
    da = res["metrics"]["auroc_diff_learned_minus_disagreement"]
    dr = res["metrics"]["rc_auc_diff_learned_minus_disagreement"]
    for d in (da, dr):
        assert "ci_lo" in d and "ci_hi" in d and "median" in d
        assert d["point"] > 0
        assert d["ci_lo"] <= d["ci_hi"]

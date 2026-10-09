"""M2.1 投稿前补强 B3:多 seed 重复 5-fold CV 单测(纯 Python,Mac 可跑)。

回应"单一确定性 5-fold"局限:打乱扰动顺序(仍 leave-perturbation-out,无泄漏)跑多个 seed,
报 learned/disagreement 的 AUROC 与 risk-coverage AUC 跨 seed 的 mean/sd/min/max,验证方向稳定。
"""
from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import repeated_cv as rc

LEDGER = "docs/findings/m1_ledger_151.jsonl"


def _entries():
    return EvalLedger.from_jsonl(LEDGER).entries


def test_structure_per_seed_and_summary():
    res = rc.repeated_cv(_entries(), seeds=(0, 1, 2))
    assert len(res["per_seed"]) == 3
    for key in ("auroc_learned", "rc_auc_learned"):
        s = res["summary"][key]
        assert {"mean", "sd", "min", "max"} <= set(s)
        assert s["min"] <= s["mean"] <= s["max"]


def test_learned_beats_disagreement_every_seed():
    res = rc.repeated_cv(_entries(), seeds=(0, 1, 2, 3, 4))
    for r in res["per_seed"]:
        assert r["auroc_learned"] > r["auroc_disagreement"]
        assert r["rc_auc_learned"] > r["rc_auc_disagreement"]


def test_mean_near_point_estimate():
    res = rc.repeated_cv(_entries(), seeds=(0, 1, 2, 3, 4))
    assert 0.85 <= res["summary"]["auroc_learned"]["mean"] <= 0.95     # 原始 0.907
    assert 0.71 <= res["summary"]["rc_auc_learned"]["mean"] <= 0.78    # 原始 0.746


def test_deterministic():
    a = rc.repeated_cv(_entries(), seeds=(0, 1, 2))
    b = rc.repeated_cv(_entries(), seeds=(0, 1, 2))
    assert a["summary"]["auroc_learned"]["mean"] == b["summary"]["auroc_learned"]["mean"]

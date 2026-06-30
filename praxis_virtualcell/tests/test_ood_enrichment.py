"""M2.1 投稿前补强 L2:OOD enrichment / OOD-only risk-coverage 单测(纯 Python,Mac 可跑)。

验证:(1) seen_in_train → OOD 标签映射正确;(2) base rate ≈ 82/151;(3) learned abstain 富集 OOD
(odds ratio > 1);(4) OOD-only 与 seen-only 子集 risk-coverage AUC 均有限(learned 在子集内仍有选择性)。
无泄漏:seen_in_train 是推理期 OOD flag(特征),非 label。
"""
import math

from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import ood_enrichment as oe

LEDGER = "docs/findings/m1_ledger_151.jsonl"


def _entries():
    return EvalLedger.from_jsonl(LEDGER).entries


def test_ood_labels_mapping():
    """seen_in_train True→非OOD(False);False→OOD(True);None→None。"""
    labs = oe.ood_labels([{"seen_in_train": True}, {"seen_in_train": False}, {"seen_in_train": None}])
    assert labs == [False, True, None]


def test_base_rate_matches_split():
    """82/151 未见 → base rate ≈ 0.543。"""
    res = oe.evaluate_ood(_entries())
    assert res["n_ood"] == 82
    assert res["n_seen"] == 69
    assert 0.53 <= res["base_rate_ood"] <= 0.55


def test_learned_abstain_enriches_ood():
    """learned 弃权/降级的扰动富集 OOD:flagged 中 OOD 占比 > base rate,odds ratio > 1。"""
    res = oe.evaluate_ood(_entries())
    assert res["learned_flagged_ood_frac"] > res["base_rate_ood"]
    assert res["odds_ratio_learned"] > 1.0


def test_subset_risk_coverage_finite():
    """OOD-only 与 seen-only 子集的 learned risk-coverage AUC 均为有限数。"""
    res = oe.evaluate_ood(_entries())
    for key in ("rc_auc_ood_only", "rc_auc_seen_only"):
        v = res[key]
        assert isinstance(v, float) and not math.isnan(v) and math.isfinite(v)

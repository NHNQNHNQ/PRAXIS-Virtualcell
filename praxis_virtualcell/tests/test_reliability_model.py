"""M2.1 Step2:轻量 Reliability Model 单测(纯 Python,Mac 可跑)。

在 151 enriched ledger 上验证:OOF dp 回归有相关性,learned bad-pert AUROC > disagreement-only > random。
"""
from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import reliability_model as rm

LEDGER = "docs/findings/m1_ledger_151.jsonl"


def test_learned_beats_single_signal_baselines():
    led = EvalLedger.from_jsonl(LEDGER)
    res = rm.evaluate(led.entries, k=5)
    a = res["auroc"]
    assert res["n"] >= 100
    assert res["reg_corr_pred_vs_true"] > 0.5            # OOF dp 回归有效
    assert a["learned"] > a["disagreement_only"]          # learned 多特征 > 单信号
    assert a["learned"] > a["ood_only"]
    assert a["disagreement_only"] > a["random"] + 0.1     # disagreement 本身强(PRAXIS 发现)
    assert a["learned"] > 0.8


def test_no_leakage_features_only():
    # evaluate 内部只经 ledger_features.extract_features(已断言无 label);此处再确认 FEATURES 不含 label
    from praxis_virtualcell.governance import ledger_features as lf
    assert not (set(rm.FEATURES) & set(lf.LABELS))

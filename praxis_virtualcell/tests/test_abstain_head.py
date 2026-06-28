"""M2.1 Step3:Learned Abstain head 单测(纯 Python,Mac 可跑)。

151 ledger 上验证 risk-coverage:learned > disagreement-only(v0.2)> random;oracle 最高;learned < oracle。
"""
from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import abstain_head as ah

LEDGER = "docs/findings/m1_ledger_151.jsonl"


def test_learned_abstain_beats_disagreement_rule():
    led = EvalLedger.from_jsonl(LEDGER)
    res = ah.evaluate_abstain(led.entries, k=5)
    auc = {k: v["auc"] for k, v in res.items()}
    assert auc["oracle"] > auc["learned"]                  # oracle 是上界
    assert auc["learned"] > auc["disagreement_only"]        # 验收:learned > v0.2 规则
    assert auc["disagreement_only"] > auc["random"]         # disagreement 本身强
    # 低 coverage 下保留集 dp 应升(选择性弃权有效)
    cur = dict(res["learned"]["curve"])
    assert cur[0.6] > cur[1.0]


def test_risk_coverage_curve_shape():
    led = EvalLedger.from_jsonl(LEDGER)
    res = ah.evaluate_abstain(led.entries, k=5)
    # 满覆盖时各信号一致(都是全集均值)
    full = {k: dict(v["curve"])[1.0] for k, v in res.items()}
    assert max(full.values()) - min(full.values()) < 1e-6

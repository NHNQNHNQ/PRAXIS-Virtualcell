"""M2.1 投稿前补强 L1:perturbation-level bootstrap CI 单测(纯 Python,Mac 可跑)。

对 151 ledger 的固定 OOF 预测 / frozen 决策做扰动级 bootstrap,给核心数字加 95% CI。
验收:(1) point estimate 复现已知 finding 数字;(2) CI 包住 point 且 lo≤hi;(3) 固定 seed 确定性;
(4) learned − disagreement 的 AUROC/AUC 差值 CI 结构正确、point>0(方向)。
"""
from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
from praxis_virtualcell.governance import bootstrap_ci as bc

LEDGER = "docs/findings/m1_ledger_151.jsonl"


def _entries():
    return EvalLedger.from_jsonl(LEDGER).entries


def test_point_estimates_reproduce_known_findings():
    """point estimate 必须复现 finding 已落地的数字(实现正确性自检)。"""
    res = bc.run(_entries(), b=200, seed=0)
    m = res["metrics"]
    assert res["n"] >= 150
    # 泛化(OOF):reliability AUROC 0.907 / disagreement 0.774
    assert 0.88 <= m["auroc_learned"]["point"] <= 0.93
    assert 0.74 <= m["auroc_disagreement"]["point"] <= 0.80
    # 泛化(OOF):risk-coverage AUC learned 0.746 / disagreement 0.720
    assert 0.72 <= m["rc_auc_learned"]["point"] <= 0.77
    assert 0.70 <= m["rc_auc_disagreement"]["point"] <= 0.74
    # in-sample 集成回放:rule_only vs learned
    assert m["mc_wrong_accept_rule"]["point"] > 0.9          # 0.974
    assert 0.15 <= m["mc_wrong_accept_learned"]["point"] <= 0.27   # 0.211
    assert m["mc_risk_coverage_rule"]["point"] < 0.10        # 0.026
    assert m["mc_risk_coverage_learned"]["point"] > 0.70     # 0.789


def test_ci_brackets_point_and_ordered():
    """每个指标:ci_lo ≤ point ≤ ci_hi,且 ci_lo ≤ median ≤ ci_hi。"""
    res = bc.run(_entries(), b=300, seed=0)
    for name, d in res["metrics"].items():
        assert d["ci_lo"] <= d["ci_hi"], name
        assert d["ci_lo"] <= d["point"] <= d["ci_hi"], name
        assert d["ci_lo"] <= d["median"] <= d["ci_hi"], name


def test_deterministic_under_fixed_seed():
    """固定 seed 两次跑出完全相同的 CI(可复现)。"""
    a = bc.run(_entries(), b=200, seed=0)
    b = bc.run(_entries(), b=200, seed=0)
    assert a["metrics"]["auroc_learned"]["ci_lo"] == b["metrics"]["auroc_learned"]["ci_lo"]
    assert a["metrics"]["auroc_learned"]["ci_hi"] == b["metrics"]["auroc_learned"]["ci_hi"]
    assert a["metrics"]["mc_wrong_accept_learned"]["ci_lo"] == b["metrics"]["mc_wrong_accept_learned"]["ci_lo"]


def test_learned_minus_disagreement_diff_present_and_directional():
    """learned − disagreement 的 AUROC / risk-cov AUC 差值:结构完整且 point>0(learned 更好的方向)。"""
    res = bc.run(_entries(), b=300, seed=0)
    da = res["metrics"]["auroc_diff_learned_minus_disagreement"]
    dr = res["metrics"]["rc_auc_diff_learned_minus_disagreement"]
    for d in (da, dr):
        assert "ci_lo" in d and "ci_hi" in d and "median" in d
        assert d["point"] > 0          # learned 优于 disagreement 的方向
        assert d["ci_lo"] <= d["ci_hi"]
